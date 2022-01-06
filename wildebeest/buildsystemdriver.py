class ProjectBuild:
    '''
    Represents a single build of a software project
    '''
    def __init__(self, folder:str) -> None:
        # don't add this until we need it, but we could potentially add a
        # .wildebeest file or folder in the build folder to keep bookkeeping like
        # status (last_action = configure)
        #
        # this would assist in a separate tool we could run to check health/status
        # which makes sense especially if I come back later and check on something
        # running on a server somewhere: wildebeest status [exp_name]
        self.folder = folder

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

    def __init__(self) -> None:
        pass

    def init(self, build:ProjectBuild):
        pass

    def configure(self, build:ProjectBuild):
        pass

    def build(self, build:ProjectBuild):
        pass

    def clean(self, build:ProjectBuild):
        pass

    def destroy(self, build:ProjectBuild):
        # if we need this, it would get rid
        pass
