#  need some dummy experiment to drive a project list so I can test out docker

from pathlib import Path
from typing import Any, Dict, List
from wildebeest import DockerBuildAlgorithm
from wildebeest.projectrecipe import ProjectRecipe
from wildebeest.runconfig import RunConfig
from wildebeest.utils import Dict, Path
from .. import Experiment
from wildebeest import ProjectList

class DockerTest(Experiment):
    def __init__(self, exp_folder:Path=None, projectlist:List[ProjectRecipe]=[], params={}) -> None:

        algorithm = DockerBuildAlgorithm(
            preprocess_steps = [
            ],
            post_build_steps = [
            ],
            postprocess_steps = [
            ])

        runconfigs = [RunConfig()]

        super().__init__('docker_test', algorithm=algorithm, runconfigs=runconfigs, projectlist=projectlist,
                        exp_folder=exp_folder, params=params)

# --- Create/run experiment
# - use docker_test_list
# - add step to build base image
# - add step to build recipe image
# - add step to build run-specific image (derived from recipe image? or do we start a fresh instance of same image??)
# - try building project in a single run - this should fail bc of dependencies
# - VERIFY failed build is captured via docker return code
# - add missing dependency in recipe
# - add step to install dependencies in recipe image
# ...get it working!!
# - VERIFY successful build is captured via docker return code
