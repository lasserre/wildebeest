from typing import Callable

class ProcessingStep:
    '''
    Represents a single processing step in an algorithm
    '''
    def __init__(self, name:str, do_step:Callable) -> None:
        # https://stackoverflow.com/questions/37835179/how-can-i-specify-the-function-type-in-my-type-hints
        self.name = name
        self.do_step = do_step

class ExperimentAlgorithm:
    def __init__(self, steps) -> None:
        pass

class Experiment:
    def __init__(self, algorithm:ExperimentAlgorithm) -> None:
        self.algorithm = algorithm

    def run(self):
        # maybe this should defer to the runner so that the runner can encapsulate
        # properly executing the algorithm serially, and eventually properly
        # managing parallel execution of jobs
        pass
