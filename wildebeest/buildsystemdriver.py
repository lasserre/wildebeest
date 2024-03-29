from importlib import metadata
from os import environ
import subprocess
from typing import Any, Callable, Dict, List

from wildebeest.sourcelanguages import LANG_C
from .runconfig import RunConfig
from .projectbuild import ProjectBuild
from .projectrecipe import BuildStepOptions
from .utils import *

class BuildSystemDriver:
    '''
    Interface class for build system drivers
    '''
    # REMEMBER: we want to be able to customize the *experiment algorithm*,
    # and we will be able to do that.
    #
    # This is different, we are not specifying the entire algorithm.
    # We need to specify this class interface in terms of independent steps
    # init, configure, build, clean
    # - post-processing is separate and not part of the build driver...it could
    #   be anything
    #
    # For the following example:
    # project.git/
    #   build.run1/
    #   build.run2/
    #
    # each build.runX folder is a separate instance of ProjectBuild, created
    # by the runner and just handed to us. we don't care about the overall
    # folder scheme, we just get handed a specific build and are asked to go do it

    def __init__(self, name:str) -> None:
        '''
        name: The name of the build system driver. This name is used by project
              recipes to identify which drivers they may use.
        '''
        self.name = name

    def _do_build_step(self, runconfig:RunConfig, build:ProjectBuild,
            opts:BuildStepOptions,
            do_step:Callable[[RunConfig, ProjectBuild], Any], **kwargs):
        '''
        This algorithm was identical for all 3 steps, so I didn't want to
        write it in 3 places :)
        '''
        with cd(build.build_folder):
            if opts.preprocess:
                opts.preprocess(runconfig, build)
            if opts.override_step:
                opts.override_step(runconfig, build, **kwargs)
            else:
                do_step(runconfig, build, **kwargs)
            if opts.postprocess:
                opts.postprocess(runconfig, build)

    def configure(self, runconfig:RunConfig, build:ProjectBuild):
        '''
        Configures the build using the options in runconfig. The code and build folders
        should already have been created at this point.
        '''
        # currently, the best method I've seen of specifying options on linux is
        # using the CC/CFLAGS style environment variables. As such, we will default to
        # setting these variables so each driver doesn't have to replicate that. If
        # a specific build system requires something different, that driver can implement it
        opts = build.recipe.configure_options
        script_name = build.recipe.config_script_name
        configure_env = runconfig.generate_env(opts.extra_cflags, opts.extra_cxxflags, opts.linker_flags)
        with env(configure_env):
            subprocess.run([f'echo Executing {self.name} configure:; ' \
                'echo CC=$CC; echo CFLAGS=$CFLAGS; '
                'echo CXX=$CXX; echo CXXFLAGS=$CXXFLAGS; ' \
                'echo LDFLAGS=$LDFLAGS'],
                           shell=True)
            self._do_build_step(runconfig, build, opts, self._do_configure, script_name=script_name)

    def build(self, runconfig:RunConfig, build:ProjectBuild, numjobs:int=1):
        '''
        Builds the project directing the build system to use the specified number of jobs
        '''
        opts = build.recipe.build_options
        numjobs = build.recipe.max_build_jobs if build.recipe.max_build_jobs > 0 else numjobs
        build_env = runconfig.generate_env(opts.extra_cflags, opts.extra_cxxflags, opts.linker_flags)
        with env(build_env):
            subprocess.run([f'echo Executing {self.name} build:; ' \
                'echo CC=$CC; echo CFLAGS=$CFLAGS; '
                'echo CXX=$CXX; echo CXXFLAGS=$CXXFLAGS; ' \
                'echo LDFLAGS=$LDFLAGS; ' \
                'echo "C compiler version ($CC):"; ' \
                '$CC --version; ' \
                'echo "C++ compiler version ($CXX):"; ' \
                '$CXX --version'],
                           shell=True)
            self._do_build_step(runconfig, build, opts, self._do_build, numjobs=numjobs)

    def clean(self, runconfig:RunConfig, build:ProjectBuild):
        '''
        Performs a clean using the build system
        '''
        opts = build.recipe.clean_options
        # probably unnecessary to define the env here, but more predictable
        # this way...can remove if never used
        clean_env = runconfig.generate_env(opts.extra_cflags, opts.extra_cxxflags, opts.linker_flags)
        with env(clean_env):
            self._do_build_step(runconfig, build, opts, self._do_clean)

    def _do_subprocess_build(self, build:ProjectBuild, build_cmd:List[str]):
        '''
        Runs the build command in a subprocess and handles capturing and writing
        stdout to a file if the build_options request it
        '''
        if build.recipe.build_options.capture_stdout:
            # capture stdout and write to file
            p = subprocess.run(build_cmd, stdout=subprocess.PIPE)
            with open(build.recipe.build_options.capture_stdout, 'w') as f:
                f.write(p.stdout.decode('utf-8'))
        else:
            p = subprocess.run(build_cmd)
        if p.returncode != 0:
            raise Exception(f'{self.name} build failed with return code {p.returncode}')

    def _do_configure(self, runconfig:RunConfig, build:ProjectBuild, **kwargs):
        '''
        Performs the build-system-specific configure step using the given options.

        When this function is called, the current working directory will be
        the project build folder
        '''
        raise NotImplementedError(f'The {self.name} build driver has not implemented _do_configure()')

    def _do_build(self, runconfig:RunConfig, build:ProjectBuild, numjobs:int=1):
        '''
        Performs the build-system-specific build step using the given options.

        When this function is called, the current working directory will be
        the project build folder
        '''
        raise NotImplementedError(f'The {self.name} build driver has not implemented _do_build()')

    def _do_clean(self, runconfig:RunConfig, build:ProjectBuild):
        '''
        Performs the build-system-specific clean step using the given options.

        When this function is called, the current working directory will be
        the project build folder
        '''
        raise NotImplementedError(f'The {self.name} build driver has not implemented _do_clean()')

class BuildSystemDriverFactory:
    def __init__(self) -> None:
        self.drivers = self._load_buildsystem_drivers()

    def _load_buildsystem_drivers(self) -> Dict[str, BuildSystemDriver]:
        '''
        Loads all BuildSystemDrivers that may be found from the
        wildebeest.build_system_drivers entry point
        '''
        driver_dict = {}
        driver_eps = metadata.entry_points()['wildebeest.build_system_drivers']
        for ep in driver_eps:
            driver_class = ep.load()
            driver_dict[driver_class().name] = driver_class
        return driver_dict

_driver_factory = None

def get_buildsystem_driver(name:str) -> BuildSystemDriver:
    '''
    Returns the BuildSystemDriver with the indicated name, or None if
    it is not a registered driver
    '''
    global _driver_factory
    if not _driver_factory:
        _driver_factory = BuildSystemDriverFactory()

    if name in _driver_factory.drivers:
        return _driver_factory.drivers[name]()  # construct a new instance
    return None
