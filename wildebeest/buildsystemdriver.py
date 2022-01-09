from os import environ
from typing import Any, Callable

from wildebeest.sourcelanguages import LANG_C
from .runconfig import RunConfig
from .projectbuild import ProjectBuild
from .projectrecipe import ProjectBuildStepOptions
from .utils import *

class BuildSystemDriver:
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
            opts:ProjectBuildStepOptions,
            do_step:Callable[[RunConfig, ProjectBuild], Any]):
        '''
        This algorithm was identical for all 3 steps, so I didn't want to
        write it in 3 places :)
        '''
        with cd(build.build_folder):
            if opts.preprocess:
                opts.preprocess(runconfig, build)
            if opts.override_step:
                opts.override_step(runconfig, build)
            else:
                do_step(runconfig, build)
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
        configure_env = runconfig.generate_env()
        with env(configure_env):
            self._do_build_step(runconfig, build, opts, self._do_configure)

    def build(self, runconfig:RunConfig, build:ProjectBuild, numjobs:int=1):
        '''
        Builds the project directing the build system to use the specified number of jobs
        '''
        opts = build.recipe.build_options
        build_env = runconfig.generate_env()
        with env(build_env):
            self._do_build_step(runconfig, build, opts, self._do_build)

    def clean(self, runconfig:RunConfig, build:ProjectBuild):
        '''
        Performs a clean using the build system
        '''
        opts = build.recipe.clean_options
        # probably unnecessary to define the env here, but more predictable
        # this way...can remove if never used
        clean_env = runconfig.generate_env()
        with env(clean_env):
            self._do_build_step(runconfig, build, opts, self._do_clean)

    def _do_configure(self, runconfig:RunConfig, build:ProjectBuild):
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