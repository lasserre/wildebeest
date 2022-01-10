from pathlib import Path
from typing import Any, Callable, List, Dict

from wildebeest.projectbuild import ProjectBuild

from .runconfig import RunConfig
from .projectrecipe import ProjectRecipe

class ProcessingStep:
    '''
    Represents a single processing step in an algorithm

    Each step's process function accepts the current RunConfig as a parameter, as well as a
    dictionary containing all currently available outputs. The dictionary maps the names of
    each ProcessingStep to the return value of that stage, and is constructed as the
    algorithm executes (the first step will get an empty dictionary).

    If any steps require particular outputs to function properly, it is the responsibility
    of the algorithm creator to ensure the steps chain together properly. Likewise,
    each ProcessingStep should document its expected input and output parameter types.

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
    def __init__(self, name:str, process:Callable[[RunConfig, Dict[str, Any]], Any],
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

class Run:
    '''
    An execution of a particular configuration in the experiment design, an experiment run

    This really encapsulates the state of the run and NOT the algorithm - the
    ExperimentAlgorithm does that and is able to execute a Run.
    '''
    def __init__(self, build:ProjectBuild, config:RunConfig) -> None:
        self.build = build
        '''The project build for this run'''

        self.config = config
        '''The run configuration'''

class ExperimentAlgorithm:
    def __init__(self, steps:List[ProcessingStep]) -> None:
        self.steps = steps
        '''A list of processing steps that define the algorithm'''

    def get_index_of_step(self, step_name:str):
        '''Returns the index of the step with the given name'''
        return next((i for i, step in enumerate(self.steps) if step.name == step_name), len(self.steps))

    def insert_before(self, step_name:str, step:ProcessingStep):
        '''Inserts the step before the step with the given name'''
        self.steps.insert(self.get_index_of_step(step_name), step)

    def insert_after(self, step_name:str, step:ProcessingStep):
        '''Inserts the step after the step with the given name'''
        self.steps.insert(self.get_index_of_step(step_name) + 1, step)

    def execute(self, run:Run):
        '''Executes the algorithm using the given RunConfig'''
        names = [x.name for x in self.steps]
        if len(set(names)) != len(names):
            print(f'The processing steps of this algorithm do not have unique names!')
            print(f'Please ensure all step names are unique and try again :)')
            return

        outputs = {}
        for step in self.steps:
            step_output = step.process(run.config, outputs)
            # if isinstance(step_output, list) and not step.do_not_parallelize:
                # TODO: we have the opportunity to partition these outputs into parallel
                # jobs according to the job manager's configuration (add them to the job pool?)
                # Job('meaningful-job-name', lambda: self.runfrom(next_step.name), job_dict)
            outputs[step.name] = step_output

class Experiment:
    def __init__(self, name:str, algorithm:ExperimentAlgorithm, projectlist:List[ProjectRecipe],
                runconfigs:List[RunConfig], exp_folder:Path=None) -> None:
        '''
        name:       A name to identify this experiment
        algorithm:  The algorithm that defines the experiment
        projectlist: The list of projects included in the experiment
        runconfigs: The set of run configs in the experiment
        exp_folder: The experiment root folder
        '''
        self.name = name
        self.algorithm = algorithm
        self.projectlist = projectlist
        self.runconfigs = runconfigs
        self.exp_folder = exp_folder if exp_folder else Path().home()/".wildebeest"/"experiments"/f'{name}.exp'

    def run(self):
        # maybe this should defer to the runner so that the runner can encapsulate
        # properly executing the algorithm serially, and eventually properly
        # managing parallel execution of jobs

        run_list = []
        for proj in self.projectlist:
            for rc in self.runconfigs:
                # TODO: determine experiment folder layout here, instantiate project
                # build for a runconfig in an experiment
                # run_list.append(Run(ProjectBuild(), rc))
                pass

        # TODO: ...I never IMPLEMENTED the default build algorithm :P go back and
        # fill that in quickly! (look up proper build driver from 'registry' using
        # name in project recipe, etc...)

        # TODO: make sure the algorithm works properly for a run where the project
        # repository folder has already been cloned from github (i.e. don't re-clone)
        # --- check this by running something with 2 run configs, make sure the second
        # build doesn't recreate the project folder!

        # TODO: once the experiment is running end-to-end for N > 1 run configs
        # SERIALLY, then instantiate a job manager here to kick off each task in
        # parallel

        for r in run_list:
            self.algorithm.execute(r)

        # For now, a job pretty much maps to a RunConfig (single build of a project)
        #
        # The experiment runner will manage (or initiate if this is broken into more classes):
        #
        #   - splitting an experiment up into Jobs (each run config is a job)
        #   - parallel job runner manages the kicking off/running of these in parallel processes (later)
        #       - define how many we want running in parallel at any one time (e.g. 8 parallel jobs),
        #         split the pile up into 8 runners, and go
        #   - something knows how to (serially) run a single Job/RunConfig (NEED THIS NOW)
        #   - A Job will hold content (RunConfig) and manages metadata about job state
