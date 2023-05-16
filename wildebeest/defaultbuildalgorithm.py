import shutil
from typing import Any, Dict, List

from wildebeest.buildsystemdriver import BuildSystemDriver, get_buildsystem_driver

from .projectrecipe import ProjectRecipe
from .experimentalgorithm import ExperimentAlgorithm
from .run import Run
from .algorithmstep import ExpStep, RunStep
from .preprocessing.repos import *

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

def reset_data_folder(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    if run.data_folder.exists():
        shutil.rmtree(run.data_folder)
    run.data_folder.mkdir(parents=True, exist_ok=True)

def clean(run:Run, outputs:Dict[str,Any]):
    '''
    Performs a build system specific clean on this build folder

    Since this is destructive, this is not part of the default algorithm. Instead,
    this helper function can be called by an experiment to clean everything if desired.
    '''
    get_driver(outputs).clean(run.config, run.build)

def DefaultBuildAlgorithm(preprocess_steps:List[ExpStep]=[],
     post_build_steps:List[RunStep]=[],
     postprocess_steps:List[ExpStep]=[]):
    '''
    Creates a new instance of the default build algorithm

    post_build_steps: Additional steps to append after the build step
    '''
    return ExperimentAlgorithm(
            preprocess_steps=[
                clone_repos(),
                *preprocess_steps
            ],
            steps=[
                RunStep('init', init),      # make this a step OUTSIDE of docker! (clone/init repo outside)
                # ...then we MIGHT be able to get away with just mapping the build folder in docker
                RunStep('configure', configure),
                RunStep('build', build),
                # reset_data resets the data folder if it exists, so if we want to
                # clean and rerun postprocessing, this is the spot to run from
                RunStep('reset_data', reset_data_folder),
                *post_build_steps
            ],
            postprocess_steps=postprocess_steps
        )

def DockerBuildAlgorithm(preprocess_steps:List[ExpStep]=[],
     pre_init_steps:List[RunStep]=[],
     pre_build_steps:List[RunStep]=[],
     post_build_steps:List[RunStep]=[],
     postprocess_steps:List[ExpStep]=[]):
    '''
    Creates a new instance of the docker build algorithm

    preprocess_steps: Additional steps to run on the experiment level before the experiment begins executing runs
    pre_init_steps: Additional steps to prepend before init. Since the docker container is created
                    during the init step, pre_init_steps won't work inside the container (since it DNE).
    pre_build_steps: Additional steps to run just before the build steps (but after init). These may run within docker
    post_build_steps: Additional steps to append after the build step (these are outside docker)
    '''
    return ExperimentAlgorithm(
            preprocess_steps=[
                clone_repos(),
                # TODO: create base docker image EXP_BASE? or just BASE
                *preprocess_steps
            ],
            steps=[
                *pre_init_steps,
                # TODO: run init outside docker and
                # - clone repos
                # - create run-specific docker image (derived from base)
                # - docker run -t -d ...
                RunStep('init', init),      # make this a step OUTSIDE of docker! (clone/init repo outside)
                # ...then we MIGHT be able to get away with just mapping the build folder in docker
                *pre_build_steps,
                RunStep('configure', configure),
                RunStep('build', build),
                # TODO: docker STOP

                # reset_data resets the data folder if it exists, so if we want to
                # clean and rerun postprocessing, this is the spot to run from
                RunStep('reset_data', reset_data_folder),
                *post_build_steps
            ],
            postprocess_steps=postprocess_steps
        )

# to allow possibly running multiple sets of commands (for different phases/runs of docker steps)
# we can just do this:

# -t: TTY
# -d: background
# docker run -t -d --name CONTAINER IMAGE
# docker exec CONTAINER wdb run --job --from X --to Y
# docker exec CONTAINER wdb run --job --from X2 --to Y2
# docker stop CONTAINER_IMAGE   # when finished for good