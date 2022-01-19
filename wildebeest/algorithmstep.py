from typing import Any, Callable, Dict
from typing import TYPE_CHECKING

from .run import Run

if TYPE_CHECKING:
    # avoid cyclic dependencies this way
    from .experiment import Experiment

class ExpStep:
    '''
    Represents a single Experiment processing step in an algorithm.

    Since the runs are executed in parallel as the main body of the experiment
    algorithm, (as of right now) it really only makes sense to run Experiment
    steps at the beginning and end of the experiment - before any runs have started
    and after all runs have completed
    '''
    def __init__(self, name:str, process:Callable[['Experiment', Dict[str,Any], Dict[str, Any]], Any],
                params:Dict[str,Any]={}) -> None:
        self.name = name
        self.process = process
        '''
        Executes this step of the algorithm. The parameters are:

        process(exp, params, outputs) -> outputs
        '''
        self.params = params

class RunStep:
    '''
    Represents a single Run processing step in an algorithm

    Each step's process function accepts as arguments the current Run, the processing
    step's parameter dictinoary, and a dictionary containing all currently available
    outputs. The output dictionary maps the names of each RunStep to the return
    value of that stage, and is constructed as the algorithm executes
    (the first step will get an empty dictionary).

    The processing step's parameter dictionary is a local collection of configuration
    parameters that can be customized per instance. This is for parameters that
    should be configurable for a single processing step implementation, but is not
    variable for that step in an algorithm (e.g. the find_instrumentation_files
    processing step indicates what file extension should be located via its
    parameter dict).

    If any steps require particular outputs of previous stages to function properly,
    it is the responsibility of the algorithm creator to ensure the steps chain together
    properly. Likewise, each RunStep should document its expected input and output parameter types.

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
    def __init__(self, name:str, process:Callable[[Run, Dict[str,Any], Dict[str, Any]], Any],
            params:Dict[str,Any]={},
            do_not_parallelize:bool=False) -> None:
        '''
        name: The unique name of this RunStep
        parameters: A dictionary of parameters for this step
        process: The Callable that executes this step in the algorithm
        '''
        # https://stackoverflow.com/questions/37835179/how-can-i-specify-the-function-type-in-my-type-hints
        self.name = name
        '''The unique name of this step'''

        self.process = process
        '''
        Executes this step of the algorithm. The parameters are:

        process(run, params, outputs) -> outputs
        '''

        self.params = params
        '''A dictionary of parameters for this step. This allows each instance of
        a processing step to be customized, but these params are constant for a
        particular algorithm step'''

        self.do_not_parallelize = do_not_parallelize
        '''Indicates that the outputs of this processing step should not be split
        into multiple parallel jobs, even if a list is returned'''
