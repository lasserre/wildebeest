from contextlib import redirect_stderr, redirect_stdout
from curses import savetty
from datetime import datetime
import multiprocessing as mp
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
from typing import Any, Callable, List

from .utils import *

class Task:
    def __init__(self, name:str, do_task:Callable[[Any], None], state:Any) -> None:
        '''
        Creates a new Task that may be run by the JobManager

        name: A name used to identify this task
        do_task: The function that is called to execute this task. The state object
                is passed as a parameter. To indicate that this task has failed, simply
                throw any exception.
        state: A state object that will be supplied to the task at execution time
        '''
        self.name = name
        self.do_task = do_task
        self.state = state

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
    def __init__(self, task:Task, workload_folder:Path, jobid:int) -> None:
        self._status = JobStatus.READY
        self.task = task
        self.jobid = jobid

        self.yamlfile = workload_folder/JobRelPaths.Jobs/f'{self.jobname}.yaml'
        self.logfile = workload_folder/JobRelPaths.Logs/f'{self.jobname}.log'

        self._pid = None
        self._starttime = None
        self._process = None
        self._error_msg = ''

        # NOTE this is the 1 and only time we save ourselves from within a Job!
        # (and here just for convenience since we don't create ourselves from
        # within a process)
        self.save_to_yaml()

    def __getstate__(self):
        state = self.__dict__.copy()
        # we have to prevent Process from being serialized bc it has an
        # AuthenticationString
        del state['_process']
        return state

    @property
    def jobname(self) -> str:
        return f'{self.task.name}.job{self.jobid}'

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
    def process(self) -> mp.Process:
        return self._process

    @process.setter
    def process(self, value:mp.Process):
        self._process = value
        self.save_to_yaml()

    @property
    def error_msg(self) -> str:
        return self._error_msg

    @error_msg.setter
    def error_msg(self, value:str):
        self._error_msg = value
        self.save_to_yaml()

    @staticmethod
    def load_from_yaml(self, yaml:Path) -> 'Job':
        return load_from_yaml(yaml)

    def save_to_yaml(self):
        save_to_yaml(self, self.yamlfile)

    def _run_job_with_logging(self):
        '''
        Nesting levels were getting deep, so for readability, this is the _run_job()
        function after logging has been redirected to job logfile
        '''
        try:
            self.task.do_task(self.task.state)
            return 0
        except Exception as e:
            traceback.print_exc()
            self.error_msg = f'Task raised exception: "{e}"'
            return 1

    def _run_job(self):
        with open(self.logfile, 'w') as log:
            # -------------------
            # TODO: pick up here
            # -------------------
            # FIX stdout/stderr issues by just launching a subprocess.run() here:
                # wdb job run <job.yaml>
            # - create wdb cmdline script to parse args, call:
                # - job.start() calls this (RENAME to job._call_wdb_run or _kick_off_subprocess)
                # - wdb job run does this:
                #     job = job.load_from_yaml(file)
                #     job._run_job_with_logging()  (RENAME to job.run())
            # - remove redirect_stdXX calls below
            # NEXT:
            # - add 'sleep' param back in to task, see if I can kill all child processes...
                # >> RUN 1 TASK FOR SANITY HERE
            # - add "wdb status" commands to check exp/job status

            # subprocess.run()
            with redirect_stderr(log):
                with redirect_stdout(sys.stderr):
                    # NOTE I think the fd's are unchanged at OS level, so if we kick off
                    # processes FROM within a task, we should manually redirect its
                    # stdout=sys.stdout, stderr=sys.stderr for that output to be redirected
                    return self._run_job_with_logging()

    def start(self) -> int:
        '''Starts the job, returning its PID'''
        self.starttime = datetime.now()
        self.process = mp.Process(target=self._run_job)
        self.process.start()
        # process doesn't get serialized, so we save pid separately
        self.pid = self.process.pid
        print(f'PID = {self.pid}')
        return self.pid

    def kill(self):
        '''Kill this job'''
        self.process.kill()

    def check_finished(self) -> bool:
        '''
        Returns true if this Job has finished running (successfully or not)

        >>> MUST BE CALLED ONLY FROM JOB MANAGER/SPAWNING PROCESS <<<
        (not within the Job process!)
        '''
        return not self.process.is_alive()

    def failed(self) -> bool:
        '''Returns true if this Job failed to complete properly'''
        if not self.process.is_alive():
            return self.process.exitcode != 0
        return False    # still running...

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
    def __init__(self, name:str, workload:List[Task], numjobs:int) -> None:
        '''
        name: Descriptive name for the workload
        workload: The tasks to be executed
        numjobs: Number of jobs to run in parallel
        '''
        self.name = name
        self.workload = workload
        self.numjobs = numjobs
        self.workload_folder = JobPaths.Workloads/f'{name}.workload'

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
        for j in self.running_jobs:
            j.kill()

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

    def start_next_job(self):
        '''Starts the next job from the ready queue'''
        next_job = self.ready_jobs.pop(0)
        self.mark_job_running(next_job)
        next_job.start()    # do I need pid return value here?
        self.running_jobs.append(next_job)
        print(f'[Started {next_job.task.name} (job {next_job.jobid})]')

    def wait_for_finished_job(self):
        '''
        Blocks until at least one job finishes running. When a job does finish,
        it is removed from the running queue and marked as finished before
        returning.
        '''
        while True:
            for j in self.running_jobs:
                if j.check_finished():
                    self.running_jobs.remove(j)
                    self.mark_job_finished(j, failed=j.failed())
                    print(f'[{j.task.name} finished]')
                    return
            time.sleep(0.25)    # 250ms?

    def start_parallel_jobs(self, max_jobs:int):
        '''Starts as many jobs as possible in parallel, up to max_jobs'''
        while self.ready_jobs and len(self.running_jobs) < max_jobs:
            self.start_next_job()

    def run(self):
        self.ready_jobs = [Job(task, self.workload_folder, i) for i, task in enumerate(self.workload)]

        MAX_JOBS = self.numjobs
        if len(self.ready_jobs) < self.numjobs:
            # we have less work than the max # jobs, so limit it
            # to the work we have (algorithm waits until pipe is full )
            MAX_JOBS = len(self.ready_jobs)

        print(f'Running {len(self.ready_jobs)} tasks using {self.numjobs} ({MAX_JOBS}) parallel jobs')

        while self.ready_jobs:
            self.start_parallel_jobs(MAX_JOBS)
            self.wait_for_finished_job()    # running jobs are full, wait for one to finish

        # wait for final jobs to finish
        while self.running_jobs:
            self.wait_for_finished_job()

        print(f'Finished running {self.name}')
