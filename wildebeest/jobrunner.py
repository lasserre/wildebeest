from curses import savetty
from pathlib import Path
import shutil
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
    ReadyJobs = Path('ready')
    RunningJobs = Path('running')
    FailedJobs = Path('failed')
    FinishedJobs = Path('done')

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
    - want to be able to check exp/job status from wherever, so that implies
    possibly in ~/.wildebeest/jobs??
    - kind of like it better in <EXP>/.wildebeest/jobs/run1.job.yaml
    >> when we start an experiment, we can mark it as running globally
        ~/.wildebeest/running/exp_name.<ID>.yaml
            - which has the path to that experiment (and we can grab all jobs from there)

    >> Experiment will save/serialize the path to its workload folder
    so status tools can find it

    ~/.wildebeest/workloads/
        exp1.workload/      # gets cleared out each time we restart it...this is TRANSIENT state
            workload_status.yaml    # WorkloadStatus object managed by JobRunner
                - holds things like # running, # done, # todo
                - names of failed runs [later]
            ready/
                run3.job3.yaml
                run4.job4.yaml
                run1.job1.yaml
            running/
                run2.job2.yaml  // run2 died, so it got stuck here
            failed/
            done/
    '''
    def __init__(self, task:Task, logfile:Path) -> None:
        self.status = JobStatus.READY
        self.task = task
        self.pid = None
        self.logfile = logfile

        # NOTE this is the 1 and only time we save ourselves from within a Job!
        # (and here just for convenience since we don't create ourselves from
        # within a process)
        self.save_to_yaml()

    @staticmethod
    def load_from_yaml(self, yaml:Path) -> 'Job':
        return load_from_yaml(yaml)

    def save_to_yaml(self):
        save_to_yaml(self, self.logfile)

    def move_logfile(self, newfile:Path):
        '''Should be called only by Job manager'''
        self.logfile = self.logfile.rename(newfile)

    def start(self) -> int:
        '''Starts the job, returning its PID'''
        # self.status = Running
        # self.starttime = now()
        # SERIALIZE NOW to avoid races..?
        #
        # subprocess.run(do_job, ... redirect output, don't wait)
        #
        # self.pid = pid
        # return pid
        pass

    def kill(self):
        '''Kill this job'''
        # we have the pid saved here, so just kill it
        pass

# could manually do it:
# create N Processes() # jobs
# for p in processes:
#   p.start()
# ..
# while not finished:
#   p.join(200ms)
#   if really joined:
#       start next job using p's slot (remove p, insert new Process)
# while some_running:
#   p.join()

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
        self.name = name
        self.workload = workload
        self.numjobs = numjobs
        self.workload_folder = JobPaths.Workloads/f'name.workload'

        self.ready_jobs = []
        self.running_jobs = []
        self.failed_jobs = []
        self.finished_jobs = []

    def __enter__(self):
        # clear out any existing executions of this workload
        if self.workload_folder.exists():
            shutil.rmtree(self.workload_folder)
        self.workload_folder.mkdir(parents=True, exist_ok=True)
        return self

    # save_to_yaml(self, PATH)

    def __exit__(self, type, value, traceback):
        # try to kill any outstanding jobs
        pass

    def run(self):
        ready_folder = self.workload_folder/JobRelPaths.ReadyJobs
        self.ready_jobs = [Job(task, ready_folder/f'{task.name}.job{i}.yaml') for i, task in enumerate(self.workload)]

        while self.ready_jobs:
            # -----------------
            # TODO pick up here, use multiprocessing.Process (within the Job class??)
            # -----------------
            next_job = self.ready_jobs.pop(0)
            # TODO MOVE logfile first...
            # next_job.move_logfile( next_job.logfile.parts)
            next_job.start()    # do I need pid return value here?
            self.running_jobs.append(next_job)

            # TODO wait for any running job to finish
            job_finished = False
            while not job_finished:
                for j in self.running_jobs:
                    if j.finished():
                        # TODO this does something like j.join(timeout_ms=100)
                        # and checks if we timed out or the job is done
                        job_finished = True
                        self.running_jobs.remove(j)
                        # TODO update state, SERIALIZE
                        # TODO MOVE to finished folder
                        break

        # - run jobs, up to N at a time
            # - loop through waiting on jobs to join...when they do, start next
            # UPDATE JOB STATE AT EACH TRANSITION, SERIALIZE

        # TODO wait for remaining jobs to finish
