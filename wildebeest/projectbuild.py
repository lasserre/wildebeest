from pathlib import Path
import shutil

from .gitrepository import GitRepository
from .projectrecipe import ProjectRecipe

class ProjectBuild:
    '''
    Represents a single build of a software project
    '''
    def __init__(self, exp_root:Path, project_root:Path, build_folder:Path, recipe:ProjectRecipe) -> None:
        '''
        exp_root: The root experiment folder
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
        self.exp_root = exp_root
        '''The experiment root folder. We store this to allow rebasing'''

        self.project_root = project_root
        '''The root source code directory for the project (typically as cloned from github)'''

        self.build_folder = build_folder
        '''The target build folder'''

        self.recipe = recipe
        '''The ProjectRecipe for this project'''

    @property
    def gitrepo(self):
        '''The git repository for this project'''
        return GitRepository(self.recipe.git_remote,
                                self.project_root,
                                head=self.recipe.git_head)

    def rebase(self, exp_root:Path):
        '''Rebase this ProjectBuild onto the given experiment root path by
        fixing any absolute paths'''
        old_exp = self.exp_root
        self.exp_root = exp_root
        self.project_root = exp_root/self.project_root.relative_to(old_exp)
        self.build_folder = exp_root/self.build_folder.relative_to(old_exp)

    def init_project_root(self):
        '''
        Creates the project source code folder, cloning it from the git repo
        '''
        if not self.project_root.exists():
            self.gitrepo.init()     # clone the project from github if it dne

    def init(self):
        '''
        Ensures the project build is initialized by cloning the project if needed
        and creating the build folder if needed. This may be called on an existing
        project build without harm.
        '''
        self.init_project_root()
        self.build_folder.mkdir(parents=True, exist_ok=True)

    def destroy(self, destroy_repo:bool=False):
        '''
        Fully removes the build folder and all of its contents

        destroy_repo:   If true, will also clean up the project_root folder
        '''
        if self.build_folder.exists():
            shutil.rmtree(self.build_folder)
        if destroy_repo and self.project_root.exists():
            shutil.rmtree(self.project_root)
