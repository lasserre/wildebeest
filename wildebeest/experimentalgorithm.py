import traceback
from typing import List

from .processingstep import ProcessingStep
from .run import Run, RunStatus

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

    def execute_from(self, step_name:str, run:Run):
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

        if not self.validate_execute_from(run, step_name):
            return

        step_idx = self.get_index_of_step(step_name)
        steps_to_exec = self.steps[step_idx:]

        # reset status, but don't overwrite outputs in case we're starting
        # mid-way through
        run.failed_step = ''
        run.status = RunStatus.RUNNING
        run.save_to_runstate_file()

        for step in steps_to_exec:
            try:
                step_output = step.process(run, step.params, run.outputs)
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
