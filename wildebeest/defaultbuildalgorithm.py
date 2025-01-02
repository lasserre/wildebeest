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

def get_exp_docker_imagename(exp:'Experiment'):
    '''Return the name of the experiment base docker image'''
    return f'wdb_{exp.name}'

def docker_image_exists(image_name:str) -> bool:
    # if docker image inspect IMAGE_NAME is successful then IMAGE_NAME exists
    p = subprocess.run(['docker', 'image', 'inspect', image_name], capture_output=True)
    return p.returncode == 0

class TemporaryDockerfile:
    '''
    Create a temporary dockerfile somewhere that gets automatically cleaned up
    when we exit a with block
    '''
    def __init__(self, dockerfile_lines:List[str]) -> None:
        self.dockerfile_lines = dockerfile_lines

    def __enter__(self) -> 'TemporaryDockerfile':
        self.tdref = tempfile.TemporaryDirectory()
        self.tdname = self.tdref.__enter__()
        self.tempdir = Path(self.tdname)
        self.dockerfile = self.tempdir/'dockerfile'
        with open(self.dockerfile, 'w') as f:
            for line in self.dockerfile_lines:
                f.write(f'{line}\n')
            f.flush()
        return self

    def docker_build(self, image_name) -> int:
        '''
        Runs docker build -t <image_name> -f <tmp_dockerfile> <folder containing tmp_dockerfile>
        and returns the returncode of the subprocess.run() command.

        If you need to build your image differently, then call subprocess.run() yourself
        without calling docker_build()
        '''
        # build the recipe image from our temporary dockerfile
        p = subprocess.run(['docker', 'build', '-t', image_name, '-f', self.dockerfile, self.dockerfile.parent])
        return p.returncode

    def __exit__(self, etype, value, traceback):
        self.tdref.__exit__(etype, value, traceback)

def create_recipe_docker_image(exp:'Experiment', recipe:ProjectRecipe, apt_arch:str):
    if docker_image_exists(recipe.docker_image_name(exp.name, apt_arch)):
        return

    dockerfile_lines = [
        f'FROM {get_exp_docker_imagename(exp)}',
    ]

    if recipe.no_cc_wrapper:
        dockerfile_lines.append('RUN rm -rf /wrapper_bin && hash -r')

    if recipe.apt_deps:
        apt_deps = recipe.apt_deps.copy()
        if apt_arch:
            # non-default arch
            apt_deps = [f'{dep}:{apt_arch}' if not dep.endswith(':all') else dep for dep in apt_deps]

        # CLS: try installing deps for all archs we want to target in the same docker image
        dockerfile_lines.append(f'RUN apt update && apt install -y {" ".join(apt_deps)}')

    with TemporaryDockerfile(dockerfile_lines) as tdf:
        rcode = tdf.docker_build(recipe.docker_image_name(exp.name, apt_arch))
        if rcode != 0:
            raise Exception(f'docker build failed to build recipe image for {recipe.name} [return code {rcode}]')

def docker_exp_setup(exp:'Experiment', params:Dict[str,Any], outputs:Dict[str,Any]):
    # create base docker image
    # right now nothing is exp-specific, so don't create a new one if it already exists globally

    exp_docker_image = get_exp_docker_imagename(exp)
    username = getpass.getuser()
    uid = os.getuid()
    gid = os.getgid()

    # create base image if it DNE
    if not docker_image_exists(BASE_DOCKER_IMAGE):
        with env({'DOCKER_BUILDKIT': '1'}):
            p = subprocess.run(['docker', 'build',
                                '--ssh', 'default',
                                '--build-arg', f'USERNAME={username}',
                                '--build-arg', f'USER_UID={uid}',
                                '--build-arg', f'USER_GID={gid}',
                                '-t', BASE_DOCKER_IMAGE, 'https://github.com/lasserre/wildebeest.git#:docker'])
            if p.returncode != 0:
                raise Exception(f'docker build failed while building base image [return code {p.returncode}]')

    # create exp image if it DNE
    if not docker_image_exists(exp_docker_image):
        dockerfile_lines = [
            f'FROM {BASE_DOCKER_IMAGE}',

            # NOTE: this could be a separate layer in-between BASE and EXP images, but
            # I just need to separate it from llvm-features so when I make wdb changes I
            # can QUICKLY pull the latest in docker and rerun. Not worth a dedicated layer right now
            'RUN pip install git+https://github.com/lasserre/wildebeest.git meson'
        ]

        if 'exp_docker_cmds' in params:
            for cmd in params['exp_docker_cmds']:
                dockerfile_lines.append(cmd)

        with TemporaryDockerfile(dockerfile_lines) as tdf:
            p = subprocess.run(['docker', 'build',
                                '--ssh', 'default',
                                '-t', exp_docker_image, '-f', tdf.dockerfile, tdf.dockerfile.parent])
            if p.returncode != 0:
                raise Exception(f'docker build failed to create experiment image "{exp_docker_image}" with return code {p.returncode}')

    other_apt_archs = list(set(rc.apt_arch for rc in exp.runconfigs if rc.apt_arch))
    apt_archs = list(set(rc.apt_arch for rc in exp.runconfigs))

    for recipe in exp.projectlist:
        for arch in apt_archs:
            create_recipe_docker_image(exp, recipe, arch)

def docker_container_exists(run:Run) -> bool:
    outstr = subprocess.check_output(['docker', 'container', 'ls', '-a']).decode('utf-8')
    return run.container_name in outstr

def docker_run(run:Run):
    '''
    Execute 'docker run' for this Run's container
    '''
    # NOTE: if needed, I can create a run-specific docker image here derived from the
    # recipe image. But I'm not sure that is needed...

    dot_wildebeest = f'{Path.home()/".wildebeest"}'

    bindmounts = [
        # experiment folder @ matching location
        f'{run.exp_root}:{run.exp_root}',
        # .wildebeest home folder (to access workloads/job.yaml files)
        f'{dot_wildebeest}:{dot_wildebeest}',
        # sync timezones so timing measurements "just work"
        '/etc/localtime:/etc/localtime:ro',
    ]

    username = getpass.getuser()

    # should I change to interactive? it would allow me to attach manually if needed...
    # no, I can run: "docker exec --user USER -it CONTAINER bash" to get a shell
    docker_run_cmd = ['docker', 'run', '--user', username, '-td', '--name', run.container_name]

    for bm in bindmounts:
        docker_run_cmd.append('-v')
        docker_run_cmd.append(bm)

    docker_run_cmd.append(run.build.recipe.docker_image_name(run.experiment.name, run.config.apt_arch))

    # -t: TTY, -d: run in background
    p = subprocess.run(docker_run_cmd)
    if p.returncode != 0:
        raise Exception(f'docker run failed for run {run.number} [return code {p.returncode}]')

def docker_restart(run:Run):
    '''Restarts the container for this run'''
    rcode = subprocess.run(f'docker restart {run.container_name}', shell=True).returncode
    if rcode != 0:
        raise Exception(f'docker restart failed for run {run.number} [return code {rcode}] - container {run.container_name}')

def docker_is_running(run:Run) -> bool:
    '''True if the docker container for this run is running'''
    grep_rcode = subprocess.run(f'docker ps | grep {run.container_name} > /dev/null', shell=True).returncode
    return bool(grep_rcode == 0)

def docker_container_exists(run:Run) -> bool:
    grep_rcode = subprocess.run(f'docker container ls -a | grep {run.container_name} > /dev/null', shell=True).returncode
    return bool(grep_rcode == 0)

def docker_attach_to_bash(run:Run, as_root:bool=False):
    username = 'root' if as_root else getpass.getuser()
    docker_exec_cmd = ['docker', 'exec', '--user', username, '-it', run.container_name, 'bash']
    p = subprocess.run(docker_exec_cmd)
    if p.returncode != 0:
        raise Exception(f'"docker exec ... bash" failed with return code {p.returncode}')

def docker_init(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    # clone repos
    outputs = init(run, params, outputs)

    # docker
    if not docker_container_exists(run):
        docker_run(run)

    # TODO: allow experiment to specify additional bindmounts? (host, container) pairs
    # TODO: should I use the --rm flag so that the container is auto-deleted when it's done running?
        # - I think this would work because I'm using bindmounts...any "progress" of the build
        # will not be lost since it's stored on the host side...

    if params['debug_docker']:
        raise Exception(f'Killing exp with docker running for debugging. Use "docker exec --user USER -it CONTAINER bash" to get a shell')

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

def DockerBuildAlgorithm(preprocess_steps:List[ExpStep]=None,
     pre_init_steps:List[RunStep]=None,
     pre_configure_steps:List[RunStep]=None,
     pre_build_steps:List[RunStep]=None,
     extra_build_steps:List[RunStep]=None,
     post_build_steps:List[RunStep]=None,
     postprocess_steps:List[ExpStep]=None):
    '''
    Creates a new instance of the docker build algorithm

    preprocess_steps: Additional steps to run on the experiment level before the experiment begins executing runs
    pre_init_steps: Additional steps to prepend before init. Since the docker container is created
                    during the init step, pre_init_steps won't work inside the container (since it DNE).
    pre_configure_steps: Additional steps to run just before the build steps (before configure but after init). These may run within docker
    pre_build_steps: Additional steps to run after configure just before the build. Can be inside docker.
    extra_build_steps: Additional steps to run just after the build, before docker cleanup (these can be inside docker)
    post_build_steps: Additional steps to append after the build step (these are outside docker)
    '''
    # use None as default param bc of Python's issues with using [] as a default parameter
    if preprocess_steps is None:
        preprocess_steps = []
    if pre_init_steps is None:
        pre_init_steps = []
    if pre_configure_steps is None:
        pre_configure_steps = []
    if pre_build_steps is None:
        pre_build_steps = []
    if extra_build_steps is None:
        extra_build_steps = []
    if post_build_steps is None:
        post_build_steps = []
    if postprocess_steps is None:
        postprocess_steps = []

    # insert docker_cleanup step after the final docker step
    post_build_modified = post_build_steps.copy()
    docker_indices = [i for i, step in enumerate(post_build_modified) if step.run_in_docker]
    last_docker_idx = max(docker_indices) if docker_indices else 0
    post_build_modified.insert(last_docker_idx+1, RunStep('docker_cleanup', docker_cleanup))

    return ExperimentAlgorithm(
            preprocess_steps=[
                clone_repos(),
                ExpStep('docker_exp_setup', docker_exp_setup),
                *preprocess_steps
            ],
            steps=[
                *pre_init_steps,
                RunStep('init', docker_init),
                *pre_configure_steps,
                RunStep('configure', configure, run_in_docker=True),
                *pre_build_steps,
                RunStep('build', build, run_in_docker=True),
                *extra_build_steps,

                # reset_data resets the data folder if it exists, so if we want to
                # clean and rerun postprocessing, this is the spot to run from
                RunStep('reset_data', reset_data_folder),
                *post_build_modified
            ],
            postprocess_steps=postprocess_steps
        )
