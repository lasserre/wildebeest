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

        # TODO: add compiler arguments to runconfigs to use our llvm-features LINKER (only)
        # >> this works for GCC or CLANG: -fuse-ld=lld (and just add the folder containing lld to PATH in base docker)
        runconfigs = [RunConfig()]

        # TODO: add other .linker-objects steps (reuse) - can I build and get .linker-objects files generated?
        # TODO: now test if I can SWITCH COMPILERS! (gcc or clang) and everything still work with llvm-features linker :D


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
