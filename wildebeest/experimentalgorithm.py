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
    def __init__(self, steps:List[RunStep],
                 preprocess_steps:List[ExpStep]=[], postprocess_steps:List[ExpStep]=[]) -> None:
        '''
        steps: The core experiment steps that are performed for each Run individually (possibly in parallel)
        preprocess_steps: Optional pre-processing steps that are performed on the entire experiment
        postprocess_steps: Optional post-processing steps that are performed on the entire experiment
        '''
        self.preprocess_steps = preprocess_steps
        '''Optional pre-processing steps that are performed on the entire experiment'''

        self.steps = steps
        '''A list of build steps'''

        self.postprocess_steps = postprocess_steps
        '''Optional post-processing steps that are performed on the entire experiment'''

    def indexof_last_contiguous_step(self, start_idx:int) -> int:
        '''
        Returns the index of the last contiguous step in the sequence beginning with run_from_step,
        where contiguous steps either all run in docker or all run outside of docker.

        Essentially this finds the end of the current "run" of docker or non-docker steps
        and returns the index of the last step in this run.

        start_idx: The index of the first step in the sequence
        '''
        docker_flags = [s.run_in_docker for s in self.steps[start_idx:]]
        try:
            change_idx = docker_flags.index(not docker_flags[0])
        except ValueError:
            return start_idx + len(docker_flags)    # all steps are the same, return last index

        # add start_idx to adjust for where we started from relative to the
        # whole list of steps
        return change_idx + start_idx

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

    def validate_execute_from_to(self, run:Run, from_step:str, to_step:str=None) -> bool:
        '''
        Validates that we can execute the algorithm from the specified step
        for this run. Returns true if this is valid, false otherwise.
        '''
        if not self.has_step(from_step):
            run.error_msg = f'No step named {from_step}'
            return False

        step_idx = self.get_index_of_step(from_step)

        # validate to_step conditions also if it was supplied
        if to_step is not None:
            if not self.has_step(to_step):
                run.error_msg = f'No step named {to_step}'
                return False
            to_idx = self.get_index_of_step(to_step)
            if step_idx >= to_idx:
                run.error_msg = f'--from step ({from_step}) is not before the --to step ({to_step})'
                print(run.error_msg)
                return False

        # validate starting step in relation to what we've completed
        if step_idx > 0:
            last_completed_idx = self.get_index_of_step(run.last_completed_step)
            no_runs_completed = run.last_completed_step == ''
            if no_runs_completed and step_idx > 0:
                msg = f"Error: can't execute from step {step_idx} '{from_step}' when step 0 '{self.steps[0].name}' hasn't been completed"
                print(msg)
                run.error_msg = msg
                return False
            elif last_completed_idx < (step_idx-1):
                lcs_name = self.steps[last_completed_idx].name
                msg = f"Can't execute from step {step_idx} '{from_step}' (last completed step is step {last_completed_idx} '{lcs_name}'"
                print(msg)
                run.error_msg = msg
                return False

        return True

    # TODO: then create DockerBuildAlgorithm and start adding prebuild steps to customize
    # the base image for a project recipe (after creating the base image in preprocessing...)

    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # NO: this will BREAK the way a Run works (current step #, last completed step, etc) and
    # we'll have to add phases with separate numbers or keep track of current phase # + current step #
    # and it all becomes a HUGE MESS
    #
    # INSTEAD: implement ALL of this at the algorithm level by doing the following:
    #       1. Each RunStep can INDIVIDUALLY specify run_in_docker=True/False
    #       2. JobRunner automatically creates "phases" artificially by splitting the
    #          "runs" of adjacent docker (or non-docker) steps into chunks that get run at once
    #       3. Each chunk is run using 'wdb run -j 1 --from <STEP_START> --to <STEP_END>'
    #       4. JobRunner launches each "chunk" in either docker, subprocess, or directly calling it
    #          based on the chunk settings
    #
    #       >> because the chunks ARE NOT EXPLICIT we don't have to add "special code" or
    #          processing to handle them - under the hood "wdb run job" just has to be
    #          able to handle running a subset of steps (from/to)
    #       >> everything else WORKS AS-IS with respect to:
    #           - 1 task per job (simple)
    #           - 1 current_step #/last completed step #...and all that logic remains the same

    # NOTE: I think I can collect all the apt packages and add a single line to
    # the dockerfile like "sudo apt update && sudo apt install p1 p2 p3 ... pN"

    # NOTE: The Run class has a .container member (or it lives in params["container"] on a run-level)
    # so that the DockerBuildRunner can locate the appropriate container for a
    # specific job to run in

    # ---- >>> it HAS to work this way since we want to call "docker run 'wdb run...'" and use
    # the filesystem to "pass state" into the docker container
    #       - if we subprocess.call(wdb run) and inside that call docker run we will try to
    #         read the YAML file for the job WE'RE CURRENTLY RUNNING! NOT GOOD

    # NOTE: docker algorithm's prebuild task HAS to create the bindmount on the image somehow...
    # (specific to this build folder, etc)

    def execute_from(self, from_step:str, run:Run, exp_params:Dict[str,Any], to_step:str=None) -> bool:
        '''
        [Re-]Executes the algorithm beginning at the specified step. Note that the
        preceding steps in the algorithm must have already been completed for this
        Run.

        steps: The appropriate list of RunSteps for this phase of the algorithm (prebuild, build, or postbuild).
               This allows us to not worry here about what is executed in docker or not, just execute this chunk
               of steps from the given step name
        step_name: Name of the step (in steps list) from which to begin
        run: The current run
        exp_params: Experiment parameters dict
        '''
        if not self.is_valid_experiment():
            run.error_msg = f'Experiment invalid - not executing'
            return False
        if not self.validate_execute_from_to(run, from_step, to_step):
            return False

        from_idx = self.get_index_of_step(from_step)
        to_idx = len(self.steps)-1 if to_step is None else self.get_index_of_step(to_step)
        steps_to_exec = self.steps[from_idx:to_idx+1]

        # reset status, but don't overwrite outputs in case we're starting
        # mid-way through
        run.failed_step = ''
        run.error_msg = ''
        run.status = RunStatus.RUNNING

        if steps_to_exec[0].name == self.steps[0].name:
            # reset all state - this will apply for initial run or reruns from beginning
            run.outputs = {}
            run.last_completed_step = ''

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

            run.save_step_runtime(step.name, datetime.now() - run.step_starttimes[step.name])
            run.outputs[step.name] = step_output
            run.last_completed_step = step.name

        if run.last_completed_step == self.steps[-1].name:
            run.status = RunStatus.FINISHED
        else:
            run.status = RunStatus.RUNNING  # this could be something new, like CHECKPOINT or PARTIAL_COMPLETE
        return True

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
