from typing import Any, Dict, List

from wildebeest.buildsystemdriver import BuildSystemDriver, get_buildsystem_driver

from .projectrecipe import ProjectRecipe
from .experimentalgorithm import ExperimentAlgorithm
from .run import Run
from .processingstep import ProcessingStep

def init(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    run.build.init()
    drivername = run.build.recipe.build_system
    driver = get_buildsystem_driver(drivername)
    if not driver:
        raise Exception(f'No build system driver registered with the name {drivername}')

    return {
        'driver': driver
    }

def get_driver(outputs:Dict[str,Any]) -> BuildSystemDriver:
    '''
    Convenience function (for type hints), should only be used after init step
    '''
    if 'init' in outputs and 'driver' in outputs['init']:
        return outputs['init']['driver']
    raise Exception('No driver saved in init output for this run')

def configure(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    get_driver(outputs).configure(run.config, run.build)

def build(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    get_driver(outputs).build(run.config, run.build, numjobs=run.config.num_build_jobs)

def clean(run:Run, outputs:Dict[str,Any]):
    '''
    Performs a build system specific clean on this build folder

    Since this is destructive, this is not part of the default algorithm. Instead,
    this helper function can be called by an experiment to clean everything if desired.
    '''
    get_driver(outputs).clean(run.config, run.build)

def DefaultBuildAlgorithm(post_build_steps:List[ProcessingStep]=[]):
    '''
    Creates a new instance of the default build algorithm

    post_build_steps: Additional steps to append after the build step
    '''
    return ExperimentAlgorithm([
        ProcessingStep('init', init),
        ProcessingStep('configure', configure),
        ProcessingStep('build', build),
        *post_build_steps
    ])
