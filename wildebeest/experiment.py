from pathlib import Path
from telnetlib import IP
from typing import List

from .defaultbuildalgorithm import clean
from .postprocessing.llvm_instrumentation import _rebase_linker_objects
from. experimentalgorithm import ExperimentAlgorithm
from .experimentpaths import ExpRelPaths
from .projectbuild import ProjectBuild
from .runconfig import RunConfig
from .run import Run
from .projectrecipe import ProjectRecipe
from .utils import *

class Experiment:
    def __init__(self, name:str, algorithm:ExperimentAlgorithm,
                runconfigs:List[RunConfig],
                projectlist:List[ProjectRecipe]=[],
                exp_folder:Path=None) -> None:
        '''
        name:       A name to identify this experiment
        algorithm:  The algorithm that defines the experiment
        runconfigs: The set of run configs in the experiment
        projectlist: The list of projects included in the experiment
        exp_folder: The experiment folder
        '''
        self.name = name
        self.algorithm = algorithm
        self.projectlist = projectlist
        self.runconfigs = runconfigs
        if not exp_folder:
            exp_folder = Path().home()/'.wildebeest'/'experiments'/f'{name}.exp'
        self.exp_folder = exp_folder

    def _rebase(self, orig_folder:Path, new_folder:Path):
        # this is all we need to do to rebase right now, if it expands then I
        # can break out into a function
        self.exp_folder = new_folder
        runlist = self._load_runs()     # loading runs rebases them

        # if we run find_binaries, we have .linker-objects
        if 'find_binaries' in [x.name for x in self.algorithm.steps]:
            for run in runlist:
                _rebase_linker_objects(orig_folder, new_folder, run.build.build_folder)

        self.save_to_yaml()
        print(f'Rebased {self.name} experiment {self.exp_folder}. Any post-processing should probably be re-run')

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

    def get_project_source_folder(self, project_name:str):
        return self.source_folder/project_name

    def get_build_folder_for_run(self, project_name:str, run_name:str):
        return self.build_folder/project_name/run_name

    def _generate_runs(self) -> List[Run]:
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
            for rc in self.runconfigs:
                project_name = recipe.name
                run_name = f'run{run_number}.{rc.name}' if rc.name else f'run{run_number}'
                build_folder = self.get_build_folder_for_run(project_name, run_name)
                source_folder = self.get_project_source_folder(project_name)
                proj_build = ProjectBuild(self.exp_folder, source_folder, build_folder, recipe)
                run_list.append(Run(run_name, self.exp_folder, proj_build, rc))
                run_number += 1
        return run_list

    def _load_runs(self) -> List[Run]:
        '''
        Loads the serialized experiment runs from the runstate folder
        '''
        yaml_files = list(self.runstates_folder.glob('*.run.yaml'))
        return [Run.load_from_runstate_file(f, self.exp_folder) for f in yaml_files]

    def run(self, force:bool=False, numjobs=1):
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
        '''
        # maybe this should defer to the runner so that the runner can encapsulate
        # properly executing the algorithm serially, and eventually properly
        # managing parallel execution of jobs
        self.save_to_yaml()

        if self.runstates_folder.exists() and not force:
            print(f'Runstates folder already exists. Either supply force=True or use rerun()')
            return

        run_list = self._generate_runs()

        # initialize the runstate files for the entire experiment
        for r in run_list:
            r.save_to_runstate_file()

        # TODO kick off jobs here!
        # ------------------------
        # subprocess.run()...
        # - redirect output to job.log

        for r in run_list:
            self.algorithm.execute(r)

    # TODO do we need this?
    def resume(self):
        '''
        Resumes each run in the experiment from its last completed state
        '''
        self.save_to_yaml()

        run_list = self._load_runs()
        if not run_list:
            print(f'No existing runs to resume in experiment {self.exp_folder}')
            return

        for r in run_list:
            idx = self.algorithm.get_index_of_step(r.last_completed_step)
            if (idx+1) < len(self.algorithm.steps):
                next_step = self.algorithm.steps[idx+1].name
                self.algorithm.execute_from(next_step, r)

    def rerun(self, step:str):
        '''
        Rerun the experiment starting from the step with the specified name.

        Since it doesn't make sense in general to start a new experiment from
        a step other than the first one, this function assumes that there are
        already existing saved runstates.
        '''
        self.save_to_yaml()

        run_list = self._load_runs()
        if not run_list:
            print(f'No existing runs to rerun in experiment {self.exp_folder}')
            return

        for r in run_list:
            self.algorithm.execute_from(step, r)

    def clean(self):
        '''
        Performs a build-system clean on all the builds in this experiment
        '''
        for run in self._load_runs():
            clean(run, run.outputs)
