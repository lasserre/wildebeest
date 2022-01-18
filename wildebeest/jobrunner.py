from datetime import datetime
from pathlib import Path
import psutil
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
    def __init__(self, task:Task, workload_folder:Path, jobid:int) -> None:
        self._status = JobStatus.READY
        self.task = task
        self.jobid = jobid

        self.yamlfile = workload_folder/JobRelPaths.Jobs/f'{self.jobname}.yaml'
        self.logfile = workload_folder/JobRelPaths.Logs/f'{self.jobname}.log'

        self._pid = None
        self._starttime = None
        self.process = None
        self._error_msg = ''

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
            self.task.do_task(self.task.state)
            return 0
        except Exception as e:
            traceback.print_exc()
            self.error_msg = f'Task raised exception: "{e}"'
            return 1

    def start_in_subprocess(self) -> int:
        '''
        Starts the job in a subprocess, returning its PID
        '''
        self.starttime = datetime.now()
        with open(self.logfile, 'w') as log:
            self.process = subprocess.Popen([f'wdb job run {self.yamlfile}'],
                shell=True, stdout=log, stderr=log)
        # process doesn't get serialized, so we save pid separately
        self.pid = self.process.pid
        return self.pid

    def kill(self):
        '''Kill this job'''
        kill_process_and_descendents(psutil.Process(self.process.pid))

    def finished(self) -> bool:
        '''
        Returns true if this Job has finished running (successfully or not)

        >>> MUST BE CALLED ONLY FROM JOB MANAGER/SPAWNING PROCESS <<<
        (not within the Job process!)
        '''
        # if returncode is None it's still running
        return self.process.poll() is not None

    def failed(self) -> bool:
        '''Returns true if this Job failed to complete properly'''
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
        pid = next_job.start_in_subprocess()
        self.running_jobs.append(next_job)
        print(f'[Started {next_job.task.name} (job {next_job.jobid}, pid = {pid})]')

    def wait_for_finished_job(self):
        '''
        Blocks until at least one job finishes running. When a job does finish,
        it is removed from the running queue and marked as finished before
        returning.
        '''
        while True:
            for j in self.running_jobs:
                if j.finished():
                    self.running_jobs.remove(j)
                    self.mark_job_finished(j, failed=j.failed())
                    if j.failed():
                        print(f'[{j.task.name} FAILED]')
                    else:
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

def run_job(yaml:Path) -> int:
    job = Job.load_from_yaml(yaml)
    return job.run()
