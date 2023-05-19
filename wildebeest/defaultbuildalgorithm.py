import getpass
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List

from wildebeest.buildsystemdriver import BuildSystemDriver, get_buildsystem_driver

from .projectrecipe import ProjectRecipe
from .experimentalgorithm import ExperimentAlgorithm
from .run import Run
from .algorithmstep import ExpStep, RunStep
from .preprocessing.repos import *
from .utils import env

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
                RunStep('init', init),
                RunStep('configure', configure),
                RunStep('build', build),
                # reset_data resets the data folder if it exists, so if we want to
                # clean and rerun postprocessing, this is the spot to run from
                RunStep('reset_data', reset_data_folder),
                *post_build_steps
            ],
            postprocess_steps=postprocess_steps
        )

BASE_DOCKER_IMAGE = 'wdb_base'

def docker_image_exists(image_name:str) -> bool:
    # if docker image inspect IMAGE_NAME is successful then IMAGE_NAME exists
    p = subprocess.run(['docker', 'image', 'inspect', image_name], capture_output=True)
    return p.returncode == 0

def create_recipe_docker_image(recipe:ProjectRecipe):
    if docker_image_exists(recipe.docker_image_name):
        return

    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        dockerfile = tmpdir/'dockerfile'

        dockerfile_lines = [
            f'FROM {BASE_DOCKER_IMAGE}\n',
        ]

        if recipe.apt_deps:
            dockerfile_lines.append(f'RUN apt update && apt install -y {" ".join(recipe.apt_deps)}\n')

        with open(dockerfile, 'w') as f:
            f.writelines(dockerfile_lines)
            f.flush()

        # build the recipe image from our temporary dockerfile
        p = subprocess.run(['docker', 'build', '-t', recipe.docker_image_name, '-f', dockerfile, dockerfile.parent])
        if p.returncode != 0:
            raise Exception(f'docker build failed to build recipe image for {recipe.name} [return code {p.returncode}]')

def docker_exp_setup(exp:'Experiment', params:Dict[str,Any], outputs:Dict[str,Any]):
    # create base docker image
    # right now nothing is exp-specific, so don't create a new one if it already exists globally

    if not docker_image_exists(BASE_DOCKER_IMAGE):
        username = getpass.getuser()
        uid = os.getuid()
        gid = os.getgid()
        with env({'DOCKER_BUILDKIT': '1'}):
            p = subprocess.run(['docker', 'build',
                                '--ssh', 'default',
                                '--build-arg', f'USERNAME={username}',
                                '--build-arg', f'USER_UID={uid}',
                                '--build-arg', f'USER_GID={gid}',
                                '-t', BASE_DOCKER_IMAGE, 'https://github.com/lasserre/wildebeest.git#docker-integration:docker'])
            if p.returncode != 0:
                raise Exception(f'docker build failed while building base image [return code {p.returncode}]')

    for recipe in exp.projectlist:
        create_recipe_docker_image(recipe)

def docker_init(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    # clone repos
    outputs = init(run, params, outputs)

    # docker
    # NOTE: if needed, I can create a run-specific docker image here derived from the
    # recipe image. But I'm not sure that is needed...

    dot_wildebeest = f'{Path.home()/".wildebeest"}'

    bindmounts = [
        # experiment folder @ matching location
        f'{run.exp_root}:{run.exp_root}',
        # .wildebeest home folder (to access workloads/job.yaml files)
        f'{dot_wildebeest}:{dot_wildebeest}',
    ]

    username = getpass.getuser()

    # should I change to interactive? it would allow me to attach manually if needed...
    docker_run_cmd = ['docker', 'run', '--user', username, '-td', '--name', run.container_name]

    for bm in bindmounts:
        docker_run_cmd.append('-v')
        docker_run_cmd.append(bm)

    docker_run_cmd.append(run.build.recipe.docker_image_name)

    # -t: TTY, -d: run in background
    p = subprocess.run(docker_run_cmd)
    if p.returncode != 0:
        raise Exception(f'docker run failed for run {run.number} [return code {p.returncode}]')

    # TODO: allow experiment to specify additional bindmounts? (host, container) pairs
    # TODO: should I use the --rm flag so that the container is auto-deleted when it's done running?
        # - I think this would work because I'm using bindmounts...any "progress" of the build
        # will not be lost since it's stored on the host side...

    return outputs

# to allow possibly running multiple sets of commands (for different phases/runs of docker steps)
# we can just do this:

# -t: TTY
# -d: background
# docker run -t -d --name CONTAINER IMAGE
# docker exec CONTAINER wdb run --job --from X --to Y
# docker exec CONTAINER wdb run --job --from X2 --to Y2
# docker stop CONTAINER_IMAGE   # when finished for good

def docker_cleanup(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    # just STOP container for now...eventually REMOVE it!
    p = subprocess.run(['docker', 'stop', run.container_name])
    if p.returncode != 0:
        # does this warrant a "failed run"?
        print(f'Failed to stop run {run.number} docker container [return code {p.returncode}]')
        return  # don't bother trying to remove it, it's still running or something

    p = subprocess.run(['docker', 'container', 'rm', run.container_name])
    if p.returncode != 0:
        print(f'Failed to remove run {run.number} docker container [return code {p.returncode}]')

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
                ExpStep('docker_exp_setup', docker_exp_setup),
                *preprocess_steps
            ],
            steps=[
                *pre_init_steps,
                RunStep('init', docker_init),
                *pre_build_steps,
                RunStep('configure', configure, run_in_docker=True),
                RunStep('build', build, run_in_docker=True),
                RunStep('docker_cleanup', docker_cleanup),

                # reset_data resets the data folder if it exists, so if we want to
                # clean and rerun postprocessing, this is the spot to run from
                RunStep('reset_data', reset_data_folder),
                *post_build_steps
            ],
            postprocess_steps=postprocess_steps
        )
