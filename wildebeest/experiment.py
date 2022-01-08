from typing import Any, Callable, List, Dict

from .runconfig import RunConfig

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
    '''
    def __init__(self, name:str, process:Callable[[RunConfig, Dict[str, Any]], Any]) -> None:
        '''
        name: The unique name of this ProcessingStep
        process: The Callable that executes this step in the algorithm
        '''
        # https://stackoverflow.com/questions/37835179/how-can-i-specify-the-function-type-in-my-type-hints
        self.name = name
        '''The unique name of this step'''

        self.process = process
        '''Executes the core processing step of the algorithm'''

class ExperimentAlgorithm:
    def __init__(self, steps:List[ProcessingStep]) -> None:
        self.steps = steps
        '''A list of processing steps that define the algorithm'''

    def execute(self, runconfig:RunConfig):
        '''Executes the algorithm using the given RunConfig'''
        names = [x.name for x in self.steps]
        if len(set(names)) != len(names):
            print(f'The processing steps of this algorithm do not have unique names!')
            print(f'Please ensure all step names are unique and try again :)')
            return

        outputs = {}
        for step in self.steps:
            outputs[step.name] = step.process(runconfig, outputs)

class Experiment:
    def __init__(self, name:str, algorithm:ExperimentAlgorithm, runs:List[RunConfig]) -> None:
        '''
        name:       A name to identify this experiment
        algorithm:  The algorithm that defines the experiment
        runs:       The set of runs in the experiment
        '''
        self.name = name
        self.algorithm = algorithm
        self.runs = runs

    def run(self):
        # maybe this should defer to the runner so that the runner can encapsulate
        # properly executing the algorithm serially, and eventually properly
        # managing parallel execution of jobs

        for r in self.runs:
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
