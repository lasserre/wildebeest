import os
from pathlib import Path
from typing import Dict
from yaml import load, dump, Loader

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

def load_from_yaml(yamlfile:Path):
    '''
    Deserializes an object from the specified yaml file
    '''
    with open(yamlfile, 'r') as f:
        return load(f.read(), Loader)

def save_to_yaml(obj, yamlfile:Path):
    '''
    Serializes the given object and writes it to the specified yaml file.
    If any part of the containing directory path doesn't exist, it will
    be created.
    '''
    yamlfile.parent.mkdir(parents=True, exist_ok=True)
    with open(yamlfile, 'w') as f:
        f.write(dump(obj))