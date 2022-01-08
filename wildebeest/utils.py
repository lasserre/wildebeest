import os
from pathlib import Path

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
