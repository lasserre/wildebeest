from pathlib import Path
import os
import subprocess
import sys

from .projectrecipe import ProjectRecipe
from .utils import cd

################################################################
# keeping this here for now until I need it...
def stdout_redirect_test():
    import subprocess
    import sys

    subprocess.run(["ls"])  # prints to stdout

    # --------------------------------------------------------
    # save stdout and redirect to log file from within process
    # (if we want to write our code using print() calls)
    # --------------------------------------------------------
    stdout = sys.stdout
    with open('captured_stdout.log', 'w') as out:
        sys.stdout = out
        # --------------------------------------------------------
        # if we call subprocess.run() in this mode, I think we have to
        # do this because subprocess.run() uses this process' original stdout??
        # (not sys.stdout by default clearly)
        # --------------------------------------------------------
        subprocess.run(['pwd'], stdout=sys.stdout)
        print('FROM THIS THING')
    sys.stdout = stdout

    subprocess.run(['w'])   # this prints to stdout again
################################################################

class GitRepository:
    '''
    Encapsulates a git project repository

    If we need to support other repos later like svn or something, we could
    make a base ProjectRepository. But I doubt we'll need it
    '''
    def __init__(self, git_remote:str, project_root:Path, head:str='') -> None:
        '''
        git_remote: The path or URL to the git remote repository
        project_root: The folder where the project should be cloned locally
        head:   If specified, this pathspec will be used to checkout a specific
                revision (branch, commit, etc) during initialization.
                If not specified, the repository will be left at the default
                HEAD (latest master/main/etc)
        '''
        self.git_remote = git_remote
        '''The path or URL to the git remote repository'''

        self.project_root = project_root
        '''The folder where the project should be cloned locally'''

        self.head = head
        '''Optional pathspec specifying the desired revision to checkout after clone'''

    def init(self):
        '''
        Clones and initializes the project repository into project_root if it doesn't
        already exist
        '''
        if self.project_root.exists() and list(self.project_root.iterdir()):
            print(f'Warning: {self.project_root} exists and is nonempty - no git operations performed')
            return

        subprocess.run(['git', 'clone', self.git_remote, str(self.project_root)])

        with cd(self.project_root):
            if self.head:
                subprocess.run(['git', 'checkout', self.head])
            subprocess.run(['git', 'submodule', 'update', '--init', '--recursive'])

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
