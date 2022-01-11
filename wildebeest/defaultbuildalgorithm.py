from typing import List

from wildebeest.buildsystemdriver import BuildSystemDriver, get_buildsystem_driver

from .projectrecipe import ProjectRecipe
from .experiment import *

def init(run:Run, outputs:Dict[str,Any]):
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
    return outputs['init']['driver']

def configure(run:Run, outputs:Dict[str,Any]):
    get_driver(outputs).configure(run.config, run.build)

def build(run:Run, outputs:Dict[str,Any]):
    get_driver(outputs).build(run.config, run.build, numjobs=run.config.num_build_jobs)

def DefaultBuildAlgorithm():
    '''
    Creates a new instance of the default build algorithm
    '''
    return ExperimentAlgorithm([
        ProcessingStep('init', init),
        ProcessingStep('configure', configure),
        ProcessingStep('build', build),
        # custom postprocessing steps will be added here
    ])
