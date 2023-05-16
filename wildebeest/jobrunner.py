from datetime import datetime, timedelta
from pathlib import Path
import psutil
import shutil
import subprocess
import sys
from termcolor import colored
import time
import traceback
from typing import Any, Callable, List

from .utils import *
from wildebeest.run import Run, RunStatus
from wildebeest import experimentalgorithm

class RunTask:
    def __init__(self, run:Run, algorithm:'experimentalgorithm.ExperimentAlgorithm', exp_params:Dict[str,Any], run_from_step:str='') -> None:
        '''
        Creates a new Task that may be run by the JobManager

        name: A name used to identify this task
        do_task: The function that is called to execute this task. The state object
                is passed as a parameter. To indicate that this task has failed, simply
                throw any exception.
        state: A state object that will be supplied to the task at execution time
        jobid: This allows the task creator to specify job ids and tie a job to the
               appropriate unit of work (e.g. Runs)
        '''
        self.run = run
        self.algorithm = algorithm
        self.exp_params = exp_params
        self.run_from_step = run_from_step
        self.name = f'Run {run.number} ({run.name})'
        self.jobid = run.number
        self.starttime:timedelta = None
        '''Start time of this task (set by job runner)'''
        self.finishtime:timedelta = None
        '''Finish time of this task (set by job runner after task is complete)'''

    @property
    def run_from_step_idx(self) -> int:
        if self.run_from_step:
            return self.algorithm.get_index_of_step(self.run_from_step)
        return 0    # no run_from_step specified, start at beginning

    @property
    def runtime(self) -> timedelta:
        '''Running time of this task up to the second (set by job runner after task is complete)'''
        rt = self.finishtime - self.starttime
        return timedelta(days=rt.days, seconds=rt.seconds)

    def _execute_run(self, from_step:str='', to_step:str=''):
        first_step = self.algorithm.steps[0].name
        last_step = self.algorithm.steps[-1].name

        # from_step (job control) overrides run_from_step since it is used to run
        # portions of a larger run_from_step sequence
        if from_step:
            first_step = from_step
        elif self.run_from_step:
            first_step = self.run_from_step

        if to_step:
            last_step = to_step

        if not self.algorithm.execute_from(first_step, self.run, self.exp_params, last_step):
            raise Exception(self.run.error_msg)

    def execute(self, from_step:str='', to_step:str=''):
        '''Executes the task'''
        self.finishtime = None
        self.on_start()

        try:
            self._execute_run(from_step, to_step)
        finally:
            # even if we failed, want to know how long it took
            self.finishtime = datetime.now()

        self.on_finished()

    def on_start(self):
        '''Pre-run actions'''
        self.run.starttime = self.starttime

    def on_finished(self):
        '''Post-run actions'''
        self.run.runtime = self.runtime

    def on_failed(self):
        '''Derived tasks can override this to indicate the task has failed'''
        # reload in case run was already updated
        self.run = Run.load_from_runstate_file(self.run.runstate_file, self.run.exp_root)

        self.run.runtime = self.runtime
        self.run.status = RunStatus.FAILED
        if not self.run.error_msg:
            self.run.error_msg = 'RunTask failed without an error message (possibly killed?)'

class JobPaths:
    Workloads = Path().home()/'.wildebeest'/'workloads'

class JobRelPaths:
    '''Relative to workload folder'''
    Jobs = Path('jobs')
    Logs = Path('logs')

class JobStatus:
    READY = 'Ready'
    RUNNING = 'Running'
    FAILED = 'Failed'
    FINISHED = 'Finished'

# remembering I want this to be QUICK/LIGHT job manager...
# are jobs tied to runs? or more generic?
class Job:
    process:subprocess.Popen

    '''
    Job Storage
    -----------
    >> Experiment will save/serialize the path to its workload folder
    so status tools can find it

    ~/.wildebeest/workloads/
        exp1.workload/      # gets cleared out each time we restart it...this is TRANSIENT state
            workload_status.yaml    # WorkloadStatus object managed by JobRunner
                - holds things like # running, # done, # todo
                - names of failed runs [later]
            jobstatus/
                run1.job1.yaml
                run2.job2.yaml  // run2 died, so it got stuck here
                run3.job3.yaml
                run4.job4.yaml
            logs/
                run1.job1.log
                ...
    '''
    def __init__(self, task:RunTask, workload_folder:Path, exp_folder:Path, jobid:int,
            debug_in_process:bool=False) -> None:
        self._status = JobStatus.READY
        self.task = task
        self.exp_folder = exp_folder    # this is so we can call wdb run -j from the proper cwd
        self.jobid = jobid
        self.yamlfile = Job.yamlfile_from_id(workload_folder, jobid)
        self.logfile = workload_folder/JobRelPaths.Logs/f'{self.jobname}.log'
        self.debug_in_process = debug_in_process
        self._running_in_docker = False      # set ONLY by JobRunner as the job changes states while running

        self._pid = None
        self._starttime = None
        self._finishtime = None
        self.process = None
        self._error_msg = ''

        self._debug_failed = False
        '''Only for debug_in_process mode, indicates if job failed'''
        self._debug_finished = False
        '''Only for debug_in_process mode, indicates if job finished'''

        # NOTE this is the 1 and only time we save ourselves from within a Job!
        # (and here just for convenience since we don't create ourselves from
        # within a process)
        self.save_to_yaml()

    def __getstate__(self):
        state = self.__dict__.copy()
        # we have to prevent Process from being serialized bc it has an
        # AuthenticationString
        if 'process' in state:
            del state['process']
        return state

    @staticmethod
    def jobname_from_id(jobid:int) -> str:
        return f'job{jobid}'

    @staticmethod
    def yamlfile_from_id(workload_folder:Path, jobid:int) -> Path:
        return workload_folder/JobRelPaths.Jobs/f'{Job.jobname_from_id(jobid)}.yaml'

    @property
    def jobname(self) -> str:
        return Job.jobname_from_id(self.jobid)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value
        self.save_to_yaml()

    @property
    def running_in_docker(self) -> bool:
        '''
        True if this job is CURRENTLY running in docker.

        This must ONLY be set by the JobRunner as the job will be changing states
        at various times while running through phases of docker and non-docker
        operation.
        '''
        return self._running_in_docker

    @running_in_docker.setter
    def running_in_docker(self, value):
        self._running_in_docker = value
        self.save_to_yaml()

    @property
    def pid(self) -> int:
        return self._pid

    @pid.setter
    def pid(self, value:int):
        self._pid = value
        self.save_to_yaml()

    @property
    def starttime(self) -> datetime:
        return self._starttime

    @starttime.setter
    def starttime(self, value:datetime):
        self._starttime = value
        self.save_to_yaml()

    @property
    def finishtime(self) -> datetime:
        return self._finishtime

    @finishtime.setter
    def finishtime(self, value:datetime):
        self._finishtime = value
        self.save_to_yaml()

    @property
    def runtime(self) -> timedelta:
        '''Returns the time (to the second) it took this job to run'''
        if self.finishtime and self.starttime:
            rt = self.finishtime - self.starttime
            # remove subsecond precision for readability...if someone wants it they can
            # subtract it themselves :)
            return timedelta(days=rt.days, seconds=rt.seconds)
        return timedelta(days=0, seconds=0)     # build probably failed

    @property
    def error_msg(self) -> str:
        return self._error_msg

    @error_msg.setter
    def error_msg(self, value:str):
        self._error_msg = value
        self.save_to_yaml()

    @staticmethod
    def load_from_yaml(yaml:Path) -> 'Job':
        return load_from_yaml(yaml)

    def save_to_yaml(self):
        save_to_yaml(self, self.yamlfile)

    def run(self, from_step:str='', to_step:str='') -> int:
        '''
        Runs this job in the current process

        from_step: Optional name of first step to begin running (this controls docker/nondocker phases,
                   and is different from experiment-wide --from control)
        to_step: Optional name of last step to run (this controls docker/nondocker phases)
        '''
        try:
            self.task.starttime = datetime.now()
            self.starttime = self.task.starttime
            self.save_to_yaml()     # save starttime in case we get killed
            self.task.execute(from_step, to_step)
            self.save_to_yaml()     # updates any modified task state
            return 0
        except Exception as e:
            traceback.print_exc()
            self.error_msg = str(e)
            return 1

    def start_in_docker(self, from_step:str, to_step:str) -> int:
        '''
        Starts the job in docker (via a subprocess), returning its PID
        '''
        cwd = self.exp_folder if self.exp_folder else Path().cwd()  # in case this wasn't specified
        with cd(cwd):
            with open(self.logfile, 'w') as log:
                self.process = subprocess.Popen([f'docker exec {self.task.run.container_name} wdb run --job {self.jobid} --from {from_step} --to {to_step}'],
                    shell=True, stdout=log, stderr=log)
        # process doesn't get serialized, so we save pid separately
        self.pid = self.process.pid
        return self.pid

    def start_in_subprocess(self, from_step:str, to_step:str) -> int:
        '''
        Starts the job in a subprocess, returning its PID
        '''
        cwd = self.exp_folder if self.exp_folder else Path().cwd()  # in case this wasn't specified
        with cd(cwd):
            with open(self.logfile, 'w') as log:
                self.process = subprocess.Popen([f'wdb run --job {self.jobid} --from {from_step} --to {to_step}'],
                    shell=True, stdout=log, stderr=log)
        # process doesn't get serialized, so we save pid separately
        self.pid = self.process.pid
        return self.pid

    def kill(self):
        '''Kill this job'''
        try:
            kill_process_and_descendents(psutil.Process(self.pid))
        except psutil.NoSuchProcess as nsp:
            if nsp.pid == self.pid:
                print(f'Looks like job {self.jobid} is no longer running')

    def finished(self) -> bool:
        '''
        Returns true if this Job has finished running (successfully or not)

        >>> MUST BE CALLED ONLY FROM JOB MANAGER/SPAWNING PROCESS <<<
        (not within the Job process!)
        '''
        if self.debug_in_process:
            return self._debug_finished
        else:
            # works for EITHER docker or nondocker (both using subprocess)
            # if returncode is None it's still running
            return self.process.poll() is not None

    def failed(self) -> bool:
        '''Returns true if this Job failed to complete properly'''
        if self.debug_in_process:
            return self._debug_failed
        else:
            # works for EITHER docker or nondocker (both using subprocess)
            return self.process.returncode != 0 if self.finished() else False

class WorkloadStatus:
    pass

"""
Philosophy is:
1. We serialize/log job state periodically as we go, so EXTERNAL tools can check status
2. THIS tool (job runner, experiment) does not return until all the jobs are done

--------------------------------------
ONLY THE JOB RUNNER MODIFIES JOB STATE - job processes do not do this!!
--------------------------------------
"""

def reset_folder(folder:Path, delete_existing:bool=False):
    '''
    Creates the folder if it does not exist. If delete_existing is specified and
    it does exist, all contents are deleted
    '''
    if delete_existing and folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)

class JobRunner:
    ready_jobs:List[Job]
    running_jobs:List[Job]
    failed_jobs:List[Job]
    finished_jobs:List[Job]

    '''
    Runs a set of Tasks (work units) using a specified max number of parallel
    jobs.
    '''
    def __init__(self, name:str, workload:List[RunTask], numjobs:int, exp_folder:Path=None,
        debug_in_process:bool=False) -> None:
        '''
        name: Descriptive name for the workload
        workload: The tasks to be executed
        numjobs: Number of jobs to run in parallel
        exp_folder: The experiment folder (this facilitates running wdb commands in new processes)
        debug_in_process: Debug flag to prevent running subprocesses - will serialize all
                          jobs and run within this process to facilitate breakpoints, etc.
        '''
        self.name = name
        self.workload = workload
        self.numjobs = numjobs
        self.workload_folder = JobPaths.Workloads/f'{name}.workload'
        self.exp_folder = exp_folder
        self.debug_in_process = debug_in_process
        if debug_in_process and self.numjobs != 1:
            print(f'Changing numjobs from {self.numjobs} to 1 because we are running in process')
            self.numjobs = 1    # by definition

        self.ready_jobs = []
        self.running_jobs = []
        self.failed_jobs = []
        self.finished_jobs = []

    def __enter__(self):
        reset_folder(self.workload_folder)
        reset_folder(self.workload_folder/JobRelPaths.Logs)
        return self

    # save_to_yaml(self, PATH)

    def __exit__(self, type, value, traceback):
        # try to kill any outstanding jobs
        try:
            for j in self.running_jobs:
                j.kill()
        except:
            pass    # oh well, we tried... :P

    def mark_job_running(self, job:Job):
        '''
        Marks a ready job as running
        '''
        if job.status != JobStatus.READY:
            print(f'Warning: trying to move a {job.status} job ({job.task.name}) to {JobStatus.RUNNING}!')
            return
        job.status = JobStatus.RUNNING

    def mark_job_finished(self, job:Job, failed:bool=False):
        '''
        Marks a running job as finished or failed, depending on the failed flag
        '''
        if job.status != JobStatus.RUNNING:
            target = JobStatus.FAILED if failed else JobStatus.FINISHED
            print(f'Warning: trying to move a {job.status} job ({job.task.name}) to {target}!')
            return
        job.status = JobStatus.FAILED if failed else JobStatus.FINISHED

        # these times should have been updated by running the task in the subprocess
        job.finishtime = job.task.finishtime

    def start_next_job(self):
        '''Starts the next job from the ready queue'''
        next_job = self.ready_jobs.pop(0)

        # this can be useful, e.g. generating unique but deterministic container names
        next_job.task.run.workload_id = self.name

        self.start_next_phase(next_job, next_job.task.run_from_step_idx)

    def start_next_phase(self, job:Job, first_step_idx:int):
        '''Starts the next phase for this job and adds it to the running job queue'''
        # detect next docker/nondocker phase
        start_idx = first_step_idx
        stop_idx = job.task.algorithm.indexof_last_contiguous_step(start_idx)
        docker_phase = job.task.algorithm.steps[start_idx].run_in_docker

        # ...now in string form to make cmd-line happy :)
        from_step = job.task.run_from_step
        to_step = job.task.algorithm.steps[stop_idx].name

        self.mark_job_running(job)
        if self.debug_in_process:
            print(f'[Started {job.task.name} (job {job.jobid}, IN PROCESS)]')
            rc = job.run()
            job._debug_finished = True
            job._debug_failed = rc != 0
        elif docker_phase:
            job.running_in_docker = True      # save this before it gets read by job
            pid = job.start_in_docker(from_step, to_step)
            print(f'[Started {job.task.name} in docker (job {job.jobid}, pid = {pid})]')
        else:
            # non-docker phase
            job.running_in_docker = False      # save this before it gets read by job
            pid = job.start_in_subprocess(from_step, to_step)
            print(f'[Started {job.task.name} (job {job.jobid}, pid = {pid})]')
        self.running_jobs.append(job)

    def handle_finished_job(self, j:Job):
        '''
        Mark finish time, move job from running list to appropriate list, print status
        '''
        failed = j.failed()     # have to read this NOW before we lose handle to process via yaml reload
        self.running_jobs.remove(j)

        # load any updated state from job process BEFORE setting any
        # new properties on this job
        j = Job.load_from_yaml(j.yamlfile)

        if failed:
            self.mark_job_finished(j, failed)
            self.failed_jobs.append(j)
            j.task.finishtime = datetime.now()  # I'm seeing finishtime not set if we get externally killed
            j.finishtime = j.task.finishtime
            j.task.on_failed()      # allow the task a chance to mark itself failed
            print(colored(f'[{j.task.name} FAILED in {j.runtime}]: {j.error_msg}', 'red', attrs=['bold']))
            return

        # did we actually COMPLETE the run, or just finish this phase?
        completed_run = j.task.run.last_completed_step == j.task.algorithm.steps[-1].name

        if completed_run:
            self.mark_job_finished(j, failed)
            self.finished_jobs.append(j)
            print(colored(f'[{j.task.name} finished in {j.runtime}]', 'green'))
        else:
            # not finished - start next phase!
            last_step_name = j.task.run.last_completed_step
            last_step_idx = j.task.algorithm.get_index_of_step(last_step_name)
            self.start_next_phase(j, last_step_idx + 1)

    def wait_for_finished_job(self):
        '''
        Blocks until at least one job finishes running. When a job does finish,
        it is removed from the running queue and marked as finished before
        returning.
        '''
        while True:
            for j in self.running_jobs:
                if j.finished():
                    self.handle_finished_job(j)
                    return
            time.sleep(0.25)    # 250ms?

    def start_parallel_jobs(self, max_jobs:int):
        '''Starts as many jobs as possible in parallel, up to max_jobs'''
        while self.ready_jobs and len(self.running_jobs) < max_jobs:
            self.start_next_job()

    def run(self) -> List[RunTask]:
        '''
        Runs the workload, and returns a list of failed Tasks (if none failed the list
        will be empty)
        '''
        self.ready_jobs = [Job(task, self.workload_folder, self.exp_folder, task.jobid, self.debug_in_process) for task in self.workload]
        self.failed_jobs = []
        self.finished_jobs = []

        MAX_JOBS = self.numjobs
        if len(self.ready_jobs) < self.numjobs:
            # we have less work than the max # jobs, so limit it
            # to the work we have (algorithm waits until pipe is full )
            MAX_JOBS = len(self.ready_jobs)

        print(f'Running {len(self.ready_jobs)} tasks using up to {MAX_JOBS} parallel jobs')
        if MAX_JOBS < self.numjobs:
            print(f'({self.numjobs} specified, but only {len(self.ready_jobs)} jobs to run)')

        while self.ready_jobs:
            self.start_parallel_jobs(MAX_JOBS)
            self.wait_for_finished_job()    # running jobs are full, wait for one to finish

        # wait for final jobs to finish
        while self.running_jobs:
            self.wait_for_finished_job()

        print(f'Finished running {self.name}')
        return [j.task for j in self.failed_jobs]

def run_job(yaml:Path, from_step:str='', to_step:str='') -> int:
    job = Job.load_from_yaml(yaml)
    return job.run(from_step, to_step)
