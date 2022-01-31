from datetime import datetime
import traceback
from typing import List, Tuple, Dict, Any
from typing import TYPE_CHECKING

from .algorithmstep import RunStep, ExpStep
from .run import Run, RunStatus

if TYPE_CHECKING:
    # avoid cyclic dependencies this way
    from .experiment import Experiment

def has_unique_stepnames(steps:List) -> bool:
    '''
    Verifies that the steps have unique names and returns True if so

    steps: A list of items that each have a .name property
    '''
    names = [x.name for x in steps]
    return len(set(names)) == len(names)

def combine_params_with_step(exp_params:Dict[str,Any], step_params:Dict[str,Any]) -> Dict[str,Any]:
    '''
    Combine the global parameters for this experiment with the given
    step-specific parameters, returning the combined parameter dictionary.

    Global experiment parameters are defaults, but step-specific parameters
    will override the global values
    '''
    combined = dict(exp_params)
    combined.update(step_params)
    return combined

class ExperimentAlgorithm:
    def __init__(self, steps:List[RunStep], preprocess_steps:List[ExpStep]=[], postprocess_steps:List[ExpStep]=[]) -> None:
        '''
        steps: The core experiment steps that are performed for each Run individually (possibly in parallel)
        preprocess_steps: Optional pre-processing steps that are performed on the entire experiment
        postprocess_steps: Optional post-processing steps that are performed on the entire experiment
        '''
        self.steps = steps
        '''A list of processing steps that define the algorithm'''
        self.preprocess_steps = preprocess_steps
        '''Optional pre-processing steps that are performed on the entire experiment'''
        self.postprocess_steps = postprocess_steps
        '''Optional post-processing steps that are performed on the entire experiment'''

    def has_step(self, step_name:str) -> bool:
        '''True if this algorithm contains a step with the given name'''
        names = [x.name for x in self.steps]
        return step_name in names

    def get_index_of_step(self, step_name:str):
        '''Returns the index of the step with the given name'''
        return next((i for i, step in enumerate(self.steps) if step.name == step_name), len(self.steps))

    def insert_before(self, step_name:str, step:RunStep):
        '''Inserts the step before the step with the given name'''
        self.steps.insert(self.get_index_of_step(step_name), step)

    def insert_after(self, step_name:str, step:RunStep):
        '''Inserts the step after the step with the given name'''
        self.steps.insert(self.get_index_of_step(step_name) + 1, step)

    def validate_execute_from(self, run:Run, step:str) -> bool:
        '''
        Validates that we can execute the algorithm from the specified step
        for this run. Returns true if this is valid, false otherwise.
        '''
        if not self.has_step(step):
            run.error_msg = f'No step named {step}'
            return False

        step_idx = self.get_index_of_step(step)

        if step_idx > 0:
            last_completed_idx = self.get_index_of_step(run.last_completed_step)
            no_runs_completed = run.last_completed_step == ''
            if no_runs_completed and step_idx > 0:
                msg = f"Error: can't execute from step {step_idx} '{step}' when step 0 '{self.steps[0].name}' hasn't been completed"
                print(msg)
                run.error_msg = msg
                return False
            elif last_completed_idx < (step_idx-1):
                lcs_name = self.steps[last_completed_idx].name
                msg = f"Can't execute from step {step_idx} '{step}' (last completed step is step {last_completed_idx} '{lcs_name}'"
                print(msg)
                run.error_msg = msg
                return False

        return True

    def execute_from(self, step_name:str, run:Run, exp_params:Dict[str,Any]) -> bool:
        '''
        [Re-]Executes the algorithm beginning at the specified step. Note that the
        preceding steps in the algorithm must have already been completed for this
        Run.

        rsfolder: The path to the experiment runstates folder
        '''
        if not self.is_valid_experiment():
            run.error_msg = f'Experiment invalid - not executing'
            return False
        if not self.validate_execute_from(run, step_name):
            return False

        step_idx = self.get_index_of_step(step_name)
        steps_to_exec = self.steps[step_idx:]

        # reset status, but don't overwrite outputs in case we're starting
        # mid-way through
        run.failed_step = ''
        run.error_msg = ''
        run.status = RunStatus.RUNNING

        for step in steps_to_exec:
            try:
                run.save_step_starttime(step.name, datetime.now())
                run.current_step = step.name
                params = combine_params_with_step(exp_params, step.params)
                step_output = step.process(run, params, run.outputs)
            except Exception as e:
                traceback.print_exc()
                print(f"Run '{run.name}' failed during the '{step.name}' step:\n\t'{e}'")
                run.save_step_runtime(step.name, datetime.now() - run.step_starttimes[step.name])
                run.status = RunStatus.FAILED
                run.failed_step = step.name
                run.error_msg = str(e)
                return False  # bail here
            # -------
            # WARNING: there are some pitfalls going this route (below), like having
            # multiple jobs trying to write to the same runstate file...we would have
            # to rethink how this works a little bit, so I'm DEFINITELY postponing for now
            # >>> it would have to be something like THIS process waits on all jobs, IF ALL
            # JOBS succeed then it grabs all their outputs and combines them into a single
            # Run output (combines all jobs into run.outputs for each step)...
            # - would have to refactor "wdb run --job" to accept a workload folder param
            #   for cases where we aren't tied to the top-level experiment
            # - NOTE could potentially save each job's run outputs in its Task class instance,
            #   since we creat them here and have handles (would have to reload from yaml)
            # -------
            # if isinstance(step_output, list) and not step.do_not_parallelize:
                # TODO: we have the opportunity to partition these outputs into parallel
                # jobs according to the job manager's configuration (add them to the job pool?)
                # ---------
                # for output in step_output:
                #   job_dict = dict(outputs)
                #   job_dict[step.name] = [output]  # only pass a subset of outputs (e.g. 1) to each job
                #   Job('meaningful-job-name', lambda: self.runfrom(next_step.name), job_dict)

            run.save_step_runtime(step.name, datetime.now() - run.step_starttimes[step.name])
            run.outputs[step.name] = step_output
            run.last_completed_step = step.name

        run.status = RunStatus.FINISHED
        return True

    def execute(self, run:Run, exp_params:Dict[str,Any]) -> bool:
        '''Executes the algorithm using the given RunConfig'''
        run.init_running_state()
        return self.execute_from(self.steps[0].name, run, exp_params)

    def is_valid_experiment(self) -> bool:
        '''Validates the experiment'''
        if not has_unique_stepnames(self.preprocess_steps):
            print(f'The preprocessing steps of this algorith do not have unique names!')
            return False

        if not has_unique_stepnames(self.steps):
            print(f'The processing steps of this algorithm do not have unique names!')
            return False

        if not has_unique_stepnames(self.postprocess_steps):
            print(f'The postprocessing steps of this algorithm do not have unique names!')
            return False

        return True

    def _do_pre_post_process(self, exp:'Experiment', steps:List[ExpStep],
            process_type:str='Pre') -> Tuple[bool, Dict[str,Any]]:
        '''
        Generic pre/post-process algorithm. I factored this out since it was identical other
        than which steps we were using.

        Returns a tuple of (return code, outputs)

        exp: Experiment to execute steps on
        steps: List of pre or post processing steps as appropriate
        process_type: Either 'Pre' or 'Post' to make logging informative :)
        '''
        if not self.is_valid_experiment():
            print(f'Experiment invalid - not executing')
            return (False, {})

        outputs = {}

        for s in steps:
            try:
                params = combine_params_with_step(exp.params, s.params)
                step_output = s.process(exp, params, outputs)
            except Exception as e:
                traceback.print_exc()
                print(f"{process_type}processing step {s.name} failed:\n\t'{e}'")
                return (False, {})
            outputs[s.name] = step_output

        return (True, outputs)

    def preprocess(self, exp:'Experiment') -> bool:
        '''
        Execute preprocessing steps on the experiment. Return True if successful
        '''
        success, outputs = self._do_pre_post_process(exp, self.preprocess_steps, 'Pre')
        exp.preprocess_outputs = outputs
        return success

    def postprocess(self, exp:'Experiment') -> bool:
        '''
        Execute postprocessing steps on the experiment. Return True if successful
        '''
        success, outputs = self._do_pre_post_process(exp, self.postprocess_steps, 'Post')
        exp.postprocess_outputs = outputs
        return success
