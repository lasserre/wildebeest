from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, List, Dict

from .experimentpaths import ExpRelPaths
from .projectbuild import ProjectBuild
from .runconfig import RunConfig
from .utils import *

class RunStatus:
    READY = 'Ready'
    RUNNING = 'Running'
    FAILED = 'Failed'
    FINISHED = 'Finished'

class Run:
    outputs: Dict[str, Any]

    '''
    An execution of a particular configuration in the experiment design, an experiment run

    This really encapsulates the state of the run and NOT the algorithm - the
    ExperimentAlgorithm does that and is able to execute a Run.
    '''
    def __init__(self, name:str, number:int, exp_root:Path, build:ProjectBuild, config:RunConfig) -> None:
        '''
        name: The name for this run
        number: The run number within the experiment
        exp_root: The root experiment folder
        build: Project build for this run
        config: Run configuration
        runstates_folder: The experiment runstates folder
        rundata_folder: The experiment rundata folder
        '''
        self.exp_root = exp_root
        '''The root experiment folder. We save this so we can rebase if needed'''

        self.name = name
        '''The name for this run'''

        self.number = number
        '''The run number for this run (within the context of its experiment)'''

        self.build = build
        '''The project build for this run'''

        self.config = config
        '''The run configuration'''

        self.workload_id = None     # filled in by JobRunner
        '''The workload id, which is unique & deterministic per exp folder location'''

        self.container_name = ''
        '''The name of the docker container for this run, if one exists'''

        self._last_completed_step = ''
        self._failed_step = ''
        self._outputs = {}
        self._status = RunStatus.READY
        self._error_msg = ''
        self._current_step = ''
        self._starttime:datetime = None
        self._runtime:timedelta = None
        self._step_starttimes:Dict[str,datetime] = {}
        self._step_runtimes:Dict[str,timedelta] = {}

    @property
    def step_starttimes(self) -> Dict[str, datetime]:
        '''Maps this run's algorithm step names to their start times'''
        return self._step_starttimes

    def save_step_starttime(self, stepname:str, starttime:datetime):
        '''
        Saves the new starttime for the given step. Since a simple property on
        the dictionary member wouldn't work for setting dict items, this ensures
        the runstate file is updated
        '''
        self._step_starttimes[stepname] = starttime
        self.save_to_runstate_file()

    @property
    def step_runtimes(self) -> Dict[str, timedelta]:
        '''Maps this run's algorithm step names to their runtimes'''
        return self._step_runtimes

    def save_step_runtime(self, stepname:str, runtime:timedelta):
        self._step_runtimes[stepname] = runtime
        self.save_to_runstate_file()

    @property
    def last_completed_step(self) -> str:
        '''The name of the last algorithm step that was completed successfully'''
        return self._last_completed_step

    @last_completed_step.setter
    def last_completed_step(self, value:str):
        self._last_completed_step = value
        self.save_to_runstate_file()

    @property
    def failed_step(self) -> str:
        '''If a failure occurs, this holds the name of the failed step'''
        return self._failed_step

    @failed_step.setter
    def failed_step(self, value:str):
        self._failed_step = value
        self.save_to_runstate_file()

    @property
    def outputs(self) -> Dict:
        '''The run outputs, where the name of each algorithm step is mapped to
        the output it returned'''
        return self._outputs

    @outputs.setter
    def outputs(self, value:Dict):
        self._outputs = value
        self.save_to_runstate_file()

    @property
    def status(self) -> str:
        '''Execution status of this run'''
        return self._status

    @status.setter
    def status(self, value:str):
        self._status = value
        self.save_to_runstate_file()

    @property
    def error_msg(self) -> str:
        '''If a failure occurs, this holds an error message'''
        return self._error_msg

    @error_msg.setter
    def error_msg(self, value:str):
        self._error_msg = value
        self.save_to_runstate_file()

    @property
    def current_step(self) -> str:
        '''While running, the algorithm will set the name of the current step
        for status info'''
        return self._current_step

    @current_step.setter
    def current_step(self, value:str):
        self._current_step = value
        self.save_to_runstate_file()

    @property
    def starttime(self) -> datetime:
        '''The start time for the last execution of this run'''
        return self._starttime

    @starttime.setter
    def starttime(self, value:datetime):
        self._starttime = value
        self.save_to_runstate_file()

    @property
    def runtime(self) -> timedelta:
        '''The runtime for the last completed execution of this run'''
        return self._runtime

    @runtime.setter
    def runtime(self, value:timedelta):
        self._runtime = value
        self.save_to_runstate_file()

    @property
    def runstate_file(self) -> Path:
        '''Returns the path to this run's runstate file'''
        return self.exp_root/ExpRelPaths.Runstates/f'run{self.number}.run.yaml'

    @property
    def data_folder(self) -> Path:
        '''
        Returns the path to this run's data foler

        rundata_folder: The experiment's rundata folder
        '''
        return self.exp_root/ExpRelPaths.Rundata/f'run{self.number}'

    def rebase(self, exp_root:Path):
        '''Rebase this Run onto the given experiment root path by
        fixing any absolute paths'''
        if self.exp_root != exp_root:
            self.exp_root = exp_root
            self.build.rebase(exp_root)
            self.save_to_runstate_file()

    @staticmethod
    def load_from_runstate_file(yamlfile:Path, exp_root:Path) -> 'Run':
        '''
        exp_root: The current experiment root folder
        '''
        run = load_from_yaml(yamlfile)
        run.rebase(exp_root)
        return run

    def save_to_runstate_file(self):
        '''Saves this Run to its runstate file'''
        save_to_yaml(self, self.runstate_file)

    def init_running_state(self):
        self._outputs = {}
        self._last_completed_step = ''
        self._failed_step = ''
        self._error_msg = ''
        self._status = RunStatus.RUNNING
        # only one file write
        self.save_to_runstate_file()
