from pathlib import Path

class GitRepository:
    '''
    Encapsulates a git project repository

    If we need to support other repos later like svn or something, we could
    make a base ProjectRepository. But I doubt we'll need it
    '''
    def __init__(self, git_remote:str, project_root:Path) -> None:
        '''

        '''
        pass

    def init(self):
        '''
        Clones and initializes the project repository if it doesn't already exist
        '''
        # full clone
        # checkout specific commit if specified
        # init/handle submodules
        pass

class ProjectBuild:
    '''
    Represents a single build of a software project
    '''
    def __init__(self, project_root:Path, build_folder:Path) -> None:
        '''
        project_root: The root directory for the project's code. This is typically
                      the folder cloned from github.
        build_folder: The target build folder. This does not need already exist.
        '''
        # don't add this until we need it, but we could potentially add a
        # .wildebeest file or folder in the build folder to keep bookkeeping like
        # status (last_action = configure)
        #
        # this would assist in a separate tool we could run to check health/status
        # which makes sense especially if I come back later and check on something
        # running on a server somewhere: wildebeest status [exp_name]
        self.project_root = project_root
        self.build_folder = build_folder

    def init(self):
        self.build_folder.mkdir(parents=True, exist_ok=True)

    def destroy(self):
        '''
        Fully removes the build folder and all of its contents
        '''
        # if we need this, it would get rid
        pass
