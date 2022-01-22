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

        self.outputs = {}
        '''The run outputs, where the name of each algorithm step is mapped to
        the output it returned'''

        self.status = RunStatus.READY
        '''Execution status of this run'''

        self.last_completed_step = ''
        '''The name of the last algorithm step that was completed successfully'''

        self.failed_step = ''
        '''If a failure occurs, this holds the name of the failed step'''

        self.error_msg = ''
        '''If a failure occurs, this holds an error message'''

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
        self.outputs = {}
        self.last_completed_step = ''
        self.failed_step = ''
        self.error_msg = ''
        self.status = RunStatus.RUNNING
