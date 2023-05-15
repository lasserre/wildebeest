import hashlib
from pathlib import Path
from typing import Any, Dict, List

from .defaultbuildalgorithm import clean
from. experimentalgorithm import ExperimentAlgorithm
from .experimentpaths import ExpRelPaths
from .jobrunner import JobRunner, RunTask
from .postprocessing.llvm_instrumentation import _rebase_linker_objects
from .projectbuild import ProjectBuild
from .projectrecipe import ProjectRecipe
from .run import Run
from .runconfig import RunConfig
from .utils import *

class ExpState:
    Ready = 'READY'
    Preprocess = 'PREPROCESSING'
    Running = 'RUNNING'
    PostProcess = 'POSTPROCESSING'
    Finished = 'FINISHED'
    Failed = 'FAILED'


class Experiment:
    postprocess_outputs:Dict[str,Any]
    workload_folder:Path

    def __init__(self, name:str, algorithm:ExperimentAlgorithm,
                runconfigs:List[RunConfig],
                projectlist:List[ProjectRecipe]=[],
                exp_folder:Path=None, params:Dict[str,Any]={}) -> None:
        '''
        name:       A name to identify this (type of) experiment
        algorithm:  The algorithm that defines the experiment
        runconfigs: The set of run configs in the experiment
        projectlist: The list of projects included in the experiment
        exp_folder: The experiment folder
        params: Any global experiment parameters. These will be combined with each
                algorithm step's own parameters and made available to each step
                in the params dictionary.
        '''
        self.name = name
        self.algorithm = algorithm
        self.projectlist = projectlist
        self.runconfigs = runconfigs
        if not exp_folder:
            exp_folder = Path().home()/'.wildebeest'/'experiments'/f'{name}.exp'
        self.exp_folder = exp_folder
        self.params = params

        self._workload_folder = None
        self._preprocess_outputs = {}
        self._postprocess_outputs = {}
        self._state = ExpState.Ready
        self._failed_step = ''

    def _rebase(self, orig_folder:Path, new_folder:Path):
        # this is all we need to do to rebase right now, if it expands then I
        # can break out into a function
        self.exp_folder = new_folder
        runlist = self.load_runs()     # loading runs rebases them

        # if we run find_binaries, we have .linker-objects
        if 'find_binaries' in [x.name for x in self.algorithm.steps]:
            for run in runlist:
                _rebase_linker_objects(orig_folder, new_folder, run.build.build_folder)

        self.save_to_yaml()
        print(f'Rebased {self.name} experiment {self.exp_folder}. Any post-processing should probably be re-run')

    @staticmethod
    def is_exp_folder(exp_folder:Path) -> bool:
        '''Returns True if exp_folder is a valid experiment folder'''
        return (exp_folder/ExpRelPaths.ExpYaml).exists()

    @staticmethod
    def load_from_yaml(exp_folder:Path) -> 'Experiment':
        yamlfile = exp_folder/ExpRelPaths.ExpYaml
        exp = load_from_yaml(yamlfile)
        orig_folder = exp.exp_folder

        if exp_folder != orig_folder:
            exp._rebase(orig_folder, exp_folder)

        return exp

    def save_to_yaml(self):
        # to keep our assumptions sensible, we don't allow saving the experiment
        # .yaml file away from its experiment folder
        yamlfile = self.exp_folder/ExpRelPaths.ExpYaml
        save_to_yaml(self, yamlfile)

    @property
    def source_folder(self):
        '''The folder containing source code for each project'''
        return self.exp_folder/ExpRelPaths.Source

    @property
    def build_folder(self):
        '''The folder containing builds for each run in the experiment'''
        return self.exp_folder/ExpRelPaths.Build

    @property
    def rundata_folder(self):
        '''The folder containing output data for individual runs in the experiment'''
        return self.exp_folder/ExpRelPaths.Rundata

    @property
    def expdata_folder(self):
        '''The folder containing experiment-level (combined) output data'''
        return self.exp_folder/ExpRelPaths.Expdata

    @property
    def runstates_folder(self):
        '''The folder containing the serialized runstates for this experiment'''
        return self.exp_folder/ExpRelPaths.Runstates

    @property
    def workload_folder(self) -> Path:
        '''Path to JobRunner's workload folder when experiment is started'''
        return self._workload_folder

    @workload_folder.setter
    def workload_folder(self, value:Path):
        self._workload_folder = value
        self.save_to_yaml()

    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, value:str):
        self._state = value
        self.save_to_yaml()

    @property
    def failed_step(self) -> str:
        return self._failed_step

    @failed_step.setter
    def failed_step(self, value:str):
        self._failed_step = value
        self.save_to_yaml()

    @property
    def postprocess_outputs(self) -> Dict[str,Any]:
        '''Any postprocessing results get saved here'''
        return self._postprocess_outputs

    @postprocess_outputs.setter
    def postprocess_outputs(self, value:Dict[str,Any]):
        self._postprocess_outputs = value
        self.save_to_yaml()

    @property
    def preprocess_outputs(self) -> Dict[str,Any]:
        '''Any preprocessing results get saved here'''
        return self._preprocess_outputs

    @preprocess_outputs.setter
    def preprocess_outputs(self, value:Dict[str,Any]):
        self._preprocess_outputs = value
        self.save_to_yaml()

    def get_project_source_folder(self, recipe:ProjectRecipe):
        if recipe.git_head:
            return self.source_folder/f'{recipe.name}@{recipe.git_head}'
        return self.source_folder/recipe.name

    def get_build_folder_for_run(self, project_name:str, run_number:int):
        return self.build_folder/project_name/f'run{run_number}'

    def _generate_runlist(self) -> List[Run]:
        '''
        Generates the experiment runs from the projectlist and runconfigs
        '''
        if not self.projectlist:
            raise Exception("Can't generate runs with an empty project list")
        if not self.runconfigs:
            raise Exception("Can't generate runs with no run configs")

        run_list = []
        run_number = 1
        for recipe in self.projectlist:
            for i, rc in enumerate(self.runconfigs):
                project_name = recipe.name
                run_name = f'{recipe.name} - {rc.name}' if len(self.runconfigs) > 1 else f'{recipe.name}'
                # NOTE: has to use run number to guarantee separate folders...sometimes we will have
                # 2 instances of the same recipe with different config tweaks. In case we forget to rename
                # one config, this is safer!
                build_folder = self.get_build_folder_for_run(project_name, run_number)
                source_folder = self.get_project_source_folder(recipe)
                proj_build = ProjectBuild(self.exp_folder, source_folder, build_folder, recipe)
                run_list.append(Run(run_name, run_number, self.exp_folder, proj_build, rc))
                run_number += 1
        return run_list

    def generate_runs(self, force:bool=False) -> List[Run]:
        '''
        Generates the experiment runlist, resets first-time experiment state, saves them to their runstate yaml
        files, and returns the resulting list of Runs
        '''
        if self.load_runs() and not force:
            raise Exception(f'generate_runs called with existing saved runstates!')

        # only reset this state for first-time/fresh runs:
        self.preprocess_outputs = {}
        self.postprocess_outputs = {}
        self.workload_folder = None

        # initialize the runs for the entire experiment
        run_list = self._generate_runlist()
        for r in run_list:
            r.save_to_runstate_file()
        return run_list

    def load_runs(self) -> List[Run]:
        '''
        Loads the serialized experiment runs from the runstate folder
        '''
        yaml_files = list(self.runstates_folder.glob('*.run.yaml'))
        return [Run.load_from_runstate_file(f, self.exp_folder) for f in yaml_files]

    def generate_workload_id(self) -> str:
        '''
        Generate a unique workload id that is deterministic for a given
        experiment folder. The idea is to reuse a given experiment's workload folder
        if we simply rerun it, but if we copy it somewhere we should have a separate
        workload folder even if they are named the same thing.
        '''
        workload_input = str(self.exp_folder)
        sha1_digest = hashlib.sha1(workload_input.encode('utf-8')).digest()
        id_string = ''.join([f'{b:02x}' for b in sha1_digest])[:8]
        return id_string

    def validate_exp_before_run(self, run_from_step:str, force:bool) -> bool:
        '''Returns true if experiment is valid and we can run it'''
        if run_from_step and not self.algorithm.has_step(run_from_step):
            print(f'No step named {run_from_step}')
            return False

        if not run_from_step:
            # we don't run from beginning if it's already been run (without -f)
            if self.runstates_folder.exists() and not force:
                run_list = self.load_runs()
                for r in run_list:
                    if r.last_completed_step:
                        print(f'Found existing runs. Either supply force=True or use rerun()')
                        return False

        # validate runconfigs are uniquely named
        if len(set([x.name for x in self.runconfigs])) < len(self.runconfigs):
            print(f'Experiment run configs are not uniquely named! Please address this and restart')
            return False

        return True

    def run(self, force:bool=False, numjobs=1, run_list:List[Run]=None, run_from_step:str='',
            no_pre:bool=False, no_post:bool=False, buildjobs:int=None,
            debug_in_process=False):
        '''
        Run the entire experiment from the beginning.

        This function expects this to be the first time the experiment is run, and
        will complain if there are existing runstates. To rerun the experiment starting
        from a particular step, use rerun(). To regenerate the experiment runs from
        updated run configs and restart it all from scratch, set force to True
        (this will delete all existing runstates).

        force: If true, will force regenerating runs from run configs, deleting existing
               runstates, and restarting this experiment.
        numjobs: The max number of parallel jobs that should be used when running this
                 experiment
        run_list: If specified, run this set of runs
        run_from_step: If specified, run beginning at this step, not from the beginning
        no_pre: Skip experiment pre-processing
        no_post: Skip experiment post-processing
        buildjobs: Number of jobs to use for each individual build (independent of numjobs).
                   Typically, this won't be used for a large set of projects, but if you
                   have a small set of large projects (e.g. 1 huge project) it can make sense
                   to use this instead of specifying # of independent parallel jobs
        debug_in_process: Prevent running jobs in subprocesses; everything will be run serially
                          within this process to support debugging/breakpoints
        '''
        if not self.validate_exp_before_run(run_from_step, force):
            return

        # ----------------------------
        # init/reset
        self.failed_step = ''       # reset this state always

        if not run_list:
            if run_from_step:
                # no run_list given - we expect to rerun all runs from this step
                run_list = self.load_runs()
                if not run_list:
                    print(f'No existing runs to rerun in experiment {self.exp_folder}')
                    return
            else:
                # --- first-time run
                run_list = self.generate_runs(force)

        # update runs to match buildjobs param if needed
        if buildjobs:
            for run in run_list:
                if run.config.num_build_jobs != buildjobs:
                    run.config.num_build_jobs = buildjobs
                    run.save_to_runstate_file()

        # -----------------
        # preprocess
        if not no_pre:
            self.state = ExpState.Preprocess
            if not self.algorithm.preprocess(self):
                self.state = ExpState.Failed
                self.failed_step = 'preprocessing'
                return

        # -----------------
        # run jobs
        self.state = ExpState.Running
        workload = [RunTask(r, self.algorithm, self.params, run_from_step) for r in run_list]
        workload_name = f"{self.name}-{self.generate_workload_id()}"
        print(f'Experiment workload name: {workload_name}')
        if run_from_step:
            print(f"Running experiment from step '{run_from_step}'")
        failed_tasks = []

        with JobRunner(workload_name, workload, numjobs, self.exp_folder, debug_in_process) as runner:
            self.workload_folder = runner.workload_folder
            failed_tasks = runner.run()

        if failed_tasks:
            print('The following runs failed:')
            print('\t', end='')
            print('\t\n'.join([t.name for t in failed_tasks]))
            print(f'{len(failed_tasks)}/{len(run_list)} runs failed in total')
            self.state = ExpState.Failed
            self.failed_step = 'run'
            return

        # -----------------
        # postprocess
        if not no_post:
            self.state = ExpState.PostProcess
            self.expdata_folder.mkdir(exist_ok=True)
            if not self.algorithm.postprocess(self):
                self.state = ExpState.Failed
                self.failed_step = 'postprocess'
                return

        self.state = ExpState.Finished

    def clean(self):
        '''
        Performs a build-system clean on all the builds in this experiment
        '''
        for run in self.load_runs():
            clean(run, run.outputs)

