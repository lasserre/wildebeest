from typing import List

from .projectrecipe import ProjectRecipe
from .experiment import *

# driver = CmakeDriver()

# build.init()
# driver.configure(runconfig, build)
# driver.build(runconfig, build, 2)

def init(rc:RunConfig, outputs:Dict[str,Any]):
    pass

def configure(rc:RunConfig, outputs:Dict[str,Any]):
    pass

def build(rc:RunConfig, outputs:Dict[str,Any]):
    pass

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
