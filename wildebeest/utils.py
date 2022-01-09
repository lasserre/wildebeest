import os
from pathlib import Path
from typing import Dict

class cd:
    def __init__(self, newpath:Path) -> None:
        '''
        newpath: The path to change directories to. Once the with block exits,
                 the current directory will be restored.
        '''
        self.newpath = newpath

    def __enter__(self):
        self.savedpath = self.newpath.cwd()
        os.chdir(self.newpath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedpath)

class env:
    def __init__(self, newvars:Dict[str,str], replace:bool=False) -> None:
        '''
        Creates an environment context using the specified environment variable
        additions/changes in the body of a with block. When the with block is exited,
        the original environment will be restored.

        newvars: New environment variables to set
        replace: If true, replaces the entire existing environment with newvars.
                 Otherwise newvars will be appended to the existing environment (default)
        '''
        self.newvars = newvars

    def __enter__(self):
        self.originalenv = dict(os.environ)
        os.environ.update(self.newvars)

    def __exit__(self, etype, value, traceback):
        os.environ.clear()
        os.environ.update(self.originalenv)
