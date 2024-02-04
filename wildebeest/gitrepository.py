from pathlib import Path
import subprocess
import shutil

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

        if self.git_remote.endswith('.tar.gz'):
            # download and unzip instead of clone
            source_folder = self.project_root.parent    # source/ folder is parent of project_root
            source_folder.mkdir(parents=True)

            # download and unpack in parent 'source' folder
            with cd(source_folder):
                subprocess.run(['wget', self.git_remote])
                tar_gz_name = self.git_remote.split('/')[-1]
                subprocess.run(['tar', 'xvzf', tar_gz_name])

                untarred_folder = [x for x in Path.cwd().iterdir() if x.name != tar_gz_name][0]
                untarred_folder.rename(self.project_root)
        else:
            # normal git repo
            subprocess.run(['git', 'clone', self.git_remote, str(self.project_root)])

            with cd(self.project_root):
                if self.head:
                    subprocess.run(['git', 'checkout', self.head])
                subprocess.run(['git', 'submodule', 'update', '--init', '--recursive'])
