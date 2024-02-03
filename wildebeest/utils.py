from datetime import timedelta
import os
from pathlib import Path
import psutil
import socket
import time
from typing import Dict
from yaml import load, dump, Loader

class print_runtime:
    '''
    Times the code inside the with block, then prints out the elapsed runtime
    when the code finished
    '''
    def __init__(self) -> None:
        '''
        newpath: The path to change directories to. Once the with block exits,
                 the current directory will be restored.
        '''
        self.start_time = 0.0
        self.stop_time = 0.0

    def __enter__(self):
        self.start_time = time.time()

    def __exit__(self, etype, value, traceback):
        self.stop_time = time.time()
        print(f'Runtime: {timedelta(seconds=int(self.runtime_sec))}')

    @property
    def runtime_sec(self) -> float:
        return self.stop_time - self.start_time

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

def kill_process(p:psutil.Process):
    parent = p.parent()
    p.kill()
    if p in parent.children():
        # handle zombie process
        p.wait(timeout=1)

def kill_descendent_processes(parent:psutil.Process):
    '''
    Kills the children of parent recursively
    '''
    for ch in parent.children():
        if ch.children():
            kill_descendent_processes(ch)
        kill_process(ch)

def kill_process_and_descendents(p:psutil.Process):
    '''
    Kills this process and all its descendents
    '''
    kill_descendent_processes(p)
    kill_process(p)

def is_port_open(port:int, host:str='localhost') -> bool:
    '''
    Returns true if the specified port is open on localhost
    (or the given host)
    '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0
