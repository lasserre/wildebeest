from datetime import timedelta
import os
import sys
from pathlib import Path
import psutil
import socket
import time
from tqdm import tqdm
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

def show_progress(iterator, total:int, use_tqdm:bool=None, progress_period:int=500):
    '''
    Show a progress indicator - either using tqdm progress bar (ideal for console output)
    or a (much less frequent) periodic print statement showing how far we have come
    (ideal for log files)

    iterator: The object being iterated over (as long as it behaves like an iterator and
              you unpack the values properly it should work)
    total:    Total number of items in the iterator, this gives flexibility with the iterator
              not being required to support len()
    use_tqdm: Use tqdm if true, print statement if false. If not specified, use_tqdm will be
              detected from sys.stdout.isatty()
    progress_period: How many items should be iterated over before a progress line is printed
    '''
    if use_tqdm is None:
        use_tqdm = sys.stdout.isatty()

    if use_tqdm:
        for x in tqdm(iterator, total=total):
            yield x
    else:
        ctr = 1
        for x in iterator:
            if ctr % progress_period == 0:
                print(f'{ctr}/{total} ({ctr/total*100:.1f}%)...', flush=True)
            ctr += 1
            yield x

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

def pretty_memsize_str(num_bytes:int, num_dec_places:int=2) -> str:
    if num_bytes > 2**30:
        return f'{num_bytes/2**30:,.{num_dec_places}f} GB'
    elif num_bytes > 2**20:
        return f'{num_bytes/2**20:,.{num_dec_places}f} MB'
    elif num_bytes > 2**10:
        return f'{num_bytes/2**10:,.{num_dec_places}f} KB'
    else:
        return f'{num_bytes:,.{num_dec_places}f} B'
