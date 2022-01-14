from pathlib import Path
import traceback
from typing import Any, Callable, List, Dict
from yaml import load, dump, Loader

from wildebeest.projectbuild import ProjectBuild

from .runconfig import RunConfig
from .projectrecipe import ProjectRecipe

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
    def __init__(self, name:str, build:ProjectBuild, config:RunConfig,
        runstates_folder:Path, rundata_folder:Path) -> None:
        '''
        name: The name for this run
        build: Project build for this run
        config: Run configuration
        runstates_folder: The experiment runstates folder
        rundata_folder: The experiment rundata folder
        '''
        self.name = name
        '''The name for this run'''

        self.build = build
        '''The project build for this run'''

        self.config = config
        '''The run configuration'''

        self.exp_runstates_folder = runstates_folder
        '''The experiment runstates folder'''

        self.exp_rundata_folder = rundata_folder
        '''The experiment rundata folder'''

        self.outputs = {}
        '''The run outputs, where the name of each algorithm step is mapped to
        the output it returned'''

        self.status = RunStatus.READY
        '''Execution status of this run'''

        self.last_completed_step = ''
        '''The name of the last algorithm step that was completed successfully'''

        self.failed_step = ''
        '''If a failure occurs, this holds the name of the failed step'''

    @property
    def runstate_file(self) -> Path:
        '''Returns the path to this run's runstate file'''
        return self.exp_runstates_folder/f'{self.name}.run.yaml'

    @property
    def data_folder(self) -> Path:
        '''
        Returns the path to this run's data foler

        rundata_folder: The experiment's rundata folder
        '''
        return self.exp_rundata_folder/f'{self.name}'

    @staticmethod
    def load_from_runstate_file(yamlfile:str) -> 'Run':
        with open(yamlfile, 'r') as f:
            return load(f.read(), Loader)

    def save_to_runstate_file(self):
        '''Saves this Run to its runstate file'''
        rsfile = self.runstate_file
        rsfile.parent.mkdir(parents=True, exist_ok=True)
        with open(rsfile, 'w') as f:
            f.write(dump(self))

    def init_running_state(self):
        self.outputs = {}
        self.last_completed_step = ''
        self.failed_step = ''
        self.status = RunStatus.RUNNING

class ProcessingStep:
    '''
    Represents a single processing step in an algorithm

    Each step's process function accepts the current Run as a parameter, as well as a
    dictionary containing all currently available outputs. The dictionary maps the names of
    each ProcessingStep to the return value of that stage, and is constructed as the
    algorithm executes (the first step will get an empty dictionary).

    If any steps require particular outputs to function properly, it is the responsibility
    of the algorithm creator to ensure the steps chain together properly. Likewise,
    each ProcessingStep should document its expected input and output parameter types.

    Failure cases
    -------------
    If a processing step fails in some way, it should raise an exception with a meaningful
    message. The algorithm runner will catch any exceptions in processing steps, log the
    offending step, update the run status as failed and bail on the run at that point.

    Parallelism
    -----------
    IF A PROCESSING STEP RETURNS A LIST, IT WILL BE INTERPRETED AS AN OPPORTUNITY
    FOR PARALLEL PROCESSING AT THE DISCRETION OF THE EXPERIMENT RUNNER.

    In other words, if a processing step returns a list of things then the list
    may be partitioned into separate jobs and run in parallel.

    Note that even for a list that gets partitioned into a sub-list per job, the
    entry for that list in each job's output dictionary will always be a list, even
    if there is only one element. It will just have fewer elements instead of all the
    original elements.

    Thus, any code that consumes these outputs can be written to expect a list,
    BUT MUST FUNCTION PROPERLY IF THE LIST IS NOT THE COMPLETE LIST. If this behavior
    is not acceptable, it can be prevented on an individual processing step's outputs
    by setting do_not_parallelize.
    '''
    def __init__(self, name:str, process:Callable[[Run, Dict[str, Any]], Any],
            do_not_parallelize:bool=False) -> None:
        '''
        name: The unique name of this ProcessingStep
        process: The Callable that executes this step in the algorithm
        '''
        # https://stackoverflow.com/questions/37835179/how-can-i-specify-the-function-type-in-my-type-hints
        self.name = name
        '''The unique name of this step'''

        self.process = process
        '''Executes the core processing step of the algorithm'''

        self.do_not_parallelize = do_not_parallelize
        '''Indicates that the outputs of this processing step should not be split
        into multiple parallel jobs, even if a list is returned'''

class ExperimentAlgorithm:
    def __init__(self, steps:List[ProcessingStep]) -> None:
        self.steps = steps
        '''A list of processing steps that define the algorithm'''

    def has_step(self, step_name:str) -> bool:
        '''True if this algorithm contains a step with the given name'''
        names = [x.name for x in self.steps]
        return step_name in names

    def get_index_of_step(self, step_name:str):
        '''Returns the index of the step with the given name'''
        return next((i for i, step in enumerate(self.steps) if step.name == step_name), len(self.steps))

    def insert_before(self, step_name:str, step:ProcessingStep):
        '''Inserts the step before the step with the given name'''
        self.steps.insert(self.get_index_of_step(step_name), step)

    def insert_after(self, step_name:str, step:ProcessingStep):
        '''Inserts the step after the step with the given name'''
        self.steps.insert(self.get_index_of_step(step_name) + 1, step)

    def validate_execute_from(self, run:Run, step:str) -> bool:
        '''
        Validates that we can execute the algorithm from the specified step
        for this run. Returns true if this is valid, false otherwise.
        '''
        if not self.has_step(step):
            print(f'No step named {step}')
            return False

        step_idx = self.get_index_of_step(step)

        if step_idx > 0:
            last_completed_idx = self.get_index_of_step(run.last_completed_step)
            no_runs_completed = run.last_completed_step == ''
            if no_runs_completed and step_idx > 0:
                print(f"Error: can't execute from step {step_idx} '{step}' when step 0 '{self.steps[0].name}' hasn't been completed")
                return False
            elif last_completed_idx < (step_idx-1):
                lcs_name = self.steps[last_completed_idx].name
                print(f"Error: can't execute from step {step_idx} '{step}' when last completed step is step {last_completed_idx} '{lcs_name}'")
                return False

        return True

    def execute_from(self, step:str, run:Run):
        '''
        [Re-]Executes the algorithm beginning at the specified step. Note that the
        preceding steps in the algorithm must have already been completed for this
        Run.

        rsfolder: The path to the experiment runstates folder
        '''
        if not self.has_unique_stepnames():
            print(f'The processing steps of this algorithm do not have unique names!')
            print(f'Please ensure all step names are unique and try again :)')
            return

        if not self.validate_execute_from(run, step):
            return

        step_idx = self.get_index_of_step(step)
        steps_to_exec = self.steps[step_idx:]

        # reset status, but don't overwrite outputs in case we're starting
        # mid-way through
        run.failed_step = ''
        run.status = RunStatus.RUNNING
        run.save_to_runstate_file()

        for step in steps_to_exec:
            try:
                step_output = step.process(run, run.outputs)
            except Exception as e:
                traceback.print_exc()
                print(f"Run '{run.name}' failed during the '{step.name}' step:\n\t'{e}'")
                run.status = RunStatus.FAILED
                run.failed_step = step.name
                run.save_to_runstate_file()
                return  # bail here
            # if isinstance(step_output, list) and not step.do_not_parallelize:
                # TODO: we have the opportunity to partition these outputs into parallel
                # jobs according to the job manager's configuration (add them to the job pool?)
                # ---------
                # for output in step_output:
                #   job_dict = dict(outputs)
                #   job_dict[step.name] = [output]  # only pass a subset of outputs (e.g. 1) to each job
                #   Job('meaningful-job-name', lambda: self.runfrom(next_step.name), job_dict)

            run.outputs[step.name] = step_output
            run.last_completed_step = step.name
            run.save_to_runstate_file()

        run.status = RunStatus.FINISHED
        run.save_to_runstate_file()

    def has_unique_stepnames(self) -> bool:
        '''Verifies that the steps have unique names and returns True if so'''
        names = [x.name for x in self.steps]
        return len(set(names)) == len(names)

    def execute(self, run:Run):
        '''Executes the algorithm using the given RunConfig'''
        run.init_running_state()
        run.save_to_runstate_file()
        self.execute_from(self.steps[0].name, run)

class Experiment:
    def __init__(self, name:str, algorithm:ExperimentAlgorithm, projectlist:List[ProjectRecipe],
                runconfigs:List[RunConfig], exp_containing_folder:Path=None) -> None:
        '''
        name:       A name to identify this experiment
        algorithm:  The algorithm that defines the experiment
        projectlist: The list of projects included in the experiment
        runconfigs: The set of run configs in the experiment
        exp_containing_folder: The folder in which to create the experiment root folder
        '''
        self.name = name
        self.algorithm = algorithm
        self.projectlist = projectlist
        self.runconfigs = runconfigs
        parent_folder = exp_containing_folder if exp_containing_folder else Path().home()/'.wildebeest'/'experiments'
        self.exp_folder = parent_folder/f'{name}.exp'

    @property
    def source_folder(self):
        '''The folder containing source code for each project'''
        return self.exp_folder/'source'

    @property
    def build_folder(self):
        '''The folder containing builds for each run in the experiment'''
        return self.exp_folder/'build'

    @property
    def rundata_folder(self):
        '''The folder containing output data for individual runs in the experiment'''
        return self.exp_folder/'rundata'

    @property
    def expdata_folder(self):
        '''The folder containing experiment-level (combined) output data'''
        return self.exp_folder/'expdata'

    @property
    def runstates_folder(self):
        '''The folder containing the serialized runstates for this experiment'''
        return self.exp_folder/'.wildebeest'/'runstates'

    def get_project_source_folder(self, project_name:str):
        return self.source_folder/project_name

    def get_build_folder_for_run(self, project_name:str, run_name:str):
        return self.build_folder/project_name/run_name

    def _generate_runs(self) -> List[Run]:
        '''
        Generates the experiment runs from the projectlist and runconfigs
        '''
        run_list = []
        run_number = 1
        for recipe in self.projectlist:
            for rc in self.runconfigs:
                project_name = recipe.project_name
                run_name = f'run{run_number}.{rc.name}' if rc.name else f'run{run_number}'
                build_folder = self.get_build_folder_for_run(project_name, run_name)
                source_folder = self.get_project_source_folder(project_name)
                proj_build = ProjectBuild(source_folder, build_folder, recipe)
                run_list.append(Run(run_name, proj_build, rc, self.runstates_folder, self.rundata_folder))
                run_number += 1
        return run_list

    def _load_runs(self) -> List[Run]:
        '''
        Loads the serialized experiment runs from the runstate folder
        '''
        yaml_files = list(self.runstates_folder.glob('*.run.yaml'))
        return [Run.load_from_runstate_file(f) for f in yaml_files]

    def run(self, force:bool=False):
        '''
        Run the entire experiment from the beginning.

        This function expects this to be the first time the experiment is run, and
        will complain if there are existing runstates. To rerun the experiment starting
        from a particular step, use rerun(). To regenerate the experiment runs from
        updated run configs and restart it all from scratch, set force to True
        (this will delete all existing runstates).

        force: If true, will force regenerating runs from run configs, deleting existing
               runstates, and restarting this experiment.
        '''
        # maybe this should defer to the runner so that the runner can encapsulate
        # properly executing the algorithm serially, and eventually properly
        # managing parallel execution of jobs

        if self.runstates_folder.exists() and not force:
            print(f'Runstates folder already exists. Either supply force=True or use rerun()')
            return

        run_list = self._generate_runs()

        # initialize the runstate files for the entire experiment
        for r in run_list:
            r.save_to_runstate_file()

        # TODO: once the experiment is running end-to-end for N > 1 run configs
        # SERIALLY, then instantiate a job manager here to kick off each Run in
        # parallel

        for r in run_list:
            self.algorithm.execute(r)

    # TODO do we need this?
    def resume(self):
        '''
        Resumes each run in the experiment from its last completed state
        '''
        run_list = self._load_runs()
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
        run_list = self._load_runs()
        if not run_list:
            print(f'No existing runs to rerun in experiment {self.exp_folder}')
            return

        for r in run_list:
            self.algorithm.execute_from(step, r)
