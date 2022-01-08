from pathlib import Path

from .projectrecipe import ProjectRecipe

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
        Clones and initializes the project repository into project_root if it doesn't
        already exist
        '''
        # full clone: git clone <remote> <project_root>
        #   - git clone creates any missing directories
        # checkout specific commit if specified
        # init/handle submodules
        #   - git submodule update --init [--recursive?]
        pass

class ProjectBuild:
    '''
    Represents a single build of a software project
    '''
    def __init__(self, project_root:Path, build_folder:Path, recipe:ProjectRecipe) -> None:
        '''
        project_root: The root directory for the project's code. This is typically
                      the folder cloned from github.
        build_folder: The target build folder. This does not need already exist.
        recipe: The project recipe with any project-specific build options
        '''
        # don't add this until we need it, but we could potentially add a
        # .wildebeest file or folder in the build folder to keep bookkeeping like
        # status (last_action = configure)
        #
        # this would assist in a separate tool we could run to check health/status
        # which makes sense especially if I come back later and check on something
        # running on a server somewhere: wildebeest status [exp_name]
        self.project_root = project_root
        '''The root source code directory for the project (typically as cloned from github)'''

        self.build_folder = build_folder
        '''The target build folder'''

        self.recipe = recipe
        '''The ProjectRecipe for this project'''

    def init(self):
        '''
        Ensures the project build is initialized by cloning the project if needed
        and creating the build folder if needed. This may be called on an existing
        project build without harm.
        '''
        # clone the project from github if this is the first time
        if not self.project_root.exists():
            repo = GitRepository(self.recipe.git_remote, self.project_root)
            repo.init()

        # make sure build folder exists
        self.build_folder.mkdir(parents=True, exist_ok=True)

    def destroy(self):
        '''
        Fully removes the build folder and all of its contents
        '''
        # if we need this, it would get rid
        pass
