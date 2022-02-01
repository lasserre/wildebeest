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

class Task:
    def __init__(self, name:str, do_task:Callable[[Any], None], state:Any, jobid:int) -> None:
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
        self.name = name
        self.do_task = do_task
        self.state = state
        self.jobid = jobid
        self.starttime:timedelta = None
        '''Start time of this task (set by job runner)'''
        self.finishtime:timedelta = None
        '''Finish time of this task (set by job runner after task is complete)'''

    @property
    def runtime(self) -> timedelta:
        '''Running time of this task up to the second (set by job runner after task is complete)'''
        rt = self.finishtime - self.starttime
        return timedelta(days=rt.days, seconds=rt.seconds)

    def execute(self):
        '''Executes the task'''
        self.finishtime = None
        self.on_start()

        try:
            self.do_task(self.state)
        finally:
            # even if we failed, want to know how long it took
            self.finishtime = datetime.now()

        self.on_finished()

    def on_start(self):
        '''Derived tasks can override this to perform pre-run actions'''
        pass

    def on_finished(self):
        '''Derived tasks can override this to perform post-run actions'''
        pass

    def on_failed(self):
        '''Derived tasks can override this to indicate the task has failed'''
        pass

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
    def __init__(self, task:Task, workload_folder:Path, exp_folder:Path, jobid:int,
            debug_in_process:bool=False) -> None:
        self._status = JobStatus.READY
        self.task = task
        self.exp_folder = exp_folder    # this is so we can call wdb run -j from the proper cwd
        self.jobid = jobid

        self.yamlfile = Job.yamlfile_from_id(workload_folder, jobid)
        self.logfile = workload_folder/JobRelPaths.Logs/f'{self.jobname}.log'

        self._pid = None
        self._starttime = None
        self._finishtime = None
        self.process = None
        self._error_msg = ''

        self.debug_in_process = debug_in_process
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

    def run(self) -> int:
        '''
        Runs this job in the current process
        '''
        try:
            self.task.starttime = datetime.now()
            self.starttime = self.task.starttime
            self.save_to_yaml()     # save starttime in case we get killed
            self.task.execute()
            self.save_to_yaml()     # updates any modified task state
            return 0
        except Exception as e:
            traceback.print_exc()
            self.error_msg = str(e)
            return 1

    def start_in_subprocess(self) -> int:
        '''
        Starts the job in a subprocess, returning its PID
        '''
        cwd = self.exp_folder if self.exp_folder else Path().cwd()  # in case this wasn't specified
        with cd(cwd):
            with open(self.logfile, 'w') as log:
                self.process = subprocess.Popen([f'wdb run --job {self.jobid}'],
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
        # if returncode is None it's still running
        return self.process.poll() is not None

    def failed(self) -> bool:
        '''Returns true if this Job failed to complete properly'''
        if self.debug_in_process:
            return self._debug_failed
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

def reset_folder(folder:Path):
    '''
    Creates the folder if it does not exist. If it does exist, all contents
    are deleted
    '''
    if folder.exists():
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
    def __init__(self, name:str, workload:List[Task], numjobs:int, exp_folder:Path=None,
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
        # clear out any existing executions of this workload
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
        self.mark_job_running(next_job)
        if self.debug_in_process:
            print(f'[Started {next_job.task.name} (job {next_job.jobid}, IN PROCESS)]')
            rc = next_job.run()
            next_job._debug_finished = True
            next_job._debug_failed = rc != 0
        else:
            pid = next_job.start_in_subprocess()
            print(f'[Started {next_job.task.name} (job {next_job.jobid}, pid = {pid})]')
        self.running_jobs.append(next_job)

    def handle_finished_job(self, j:Job):
        '''
        Mark finish time, move job from running list to appropriate list, print status
        '''
        failed = j.failed()     # have to read this NOW before we lose handle to process via yaml reload
        self.running_jobs.remove(j)

        # load any updated state from job process BEFORE setting any
        # new properties on this job
        j = Job.load_from_yaml(j.yamlfile)
        self.mark_job_finished(j, failed)

        if failed:
            self.failed_jobs.append(j)
            j.task.finishtime = datetime.now()  # I'm seeing finishtime not set if we get externally killed
            j.finishtime = j.task.finishtime
            j.task.on_failed()      # allow the task a chance to mark itself failed
            print(colored(f'[{j.task.name} FAILED in {j.runtime}]: {j.error_msg}', 'red', attrs=['bold']))
        else:
            self.finished_jobs.append(j)
            print(colored(f'[{j.task.name} finished in {j.runtime}]', 'green'))

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

    def run(self) -> List[Task]:
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

def run_job(yaml:Path) -> int:
    job = Job.load_from_yaml(yaml)
    return job.run()
