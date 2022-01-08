from .runconfig import RunConfig
from .projectbuild import ProjectBuild

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

    def configure(self, runconfig:RunConfig, build:ProjectBuild):
        '''
        Configures the build using the options in runconfig. The code and build folders
        should already have been created at this point.
        '''
        # TODO: the build system driver (ideally implemented in the generic one)
        # should handle any extra pre/post steps specific to project recipes...
        # these should NOT be considered part of the experiment ALGORITHM - these
        # are not generic to experiment - they are project-specific steps that
        # can be thought of as part of the build system configure/build/etc. steps
        pass

    def build(self, build:ProjectBuild, numjobs:int=1):
        '''
        Builds the project directing the build system to use the specified number of jobs
        '''
        pass

    def clean(self, build:ProjectBuild):
        '''
        Performs a clean using the build system
        '''
        pass
