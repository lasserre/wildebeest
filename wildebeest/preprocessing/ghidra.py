from pathlib import Path
import subprocess
from typing import Any, Dict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # avoid cyclic dependencies this way
    from ..experiment import Experiment

from ..experimentalgorithm import ExpStep
from ..utils import *

class GhidraKeys:
    GHIDRA_INSTALL = 'GHIDRA_INSTALL'
    GHIDRA_USER = 'GHIDRA_USER'
    GHIDRA_PWD = 'GHIDRA_PWD'
    GHIDRA_REPO = 'GHIDRA_REPO'

def _start_ghidra_server(exp:'Experiment', params:Dict[str,Any], outputs:Dict[str,Any]):
    '''
    Checks to make sure ghidra server is running on the default port. If not, the
    ghidra server is started (as current user) in a new tmux window
    '''
    if GhidraKeys.GHIDRA_INSTALL not in params:
        raise Exception(f'Required parameter {GhidraKeys.GHIDRA_INSTALL} not in params!')

    if not is_port_open(13100):
        # start ghidra server...
        ghidra_home = Path(params[GhidraKeys.GHIDRA_INSTALL])
        ghidraSvr = ghidra_home/'server'/'ghidraSvr'
        # tmux new-window "<ghidra_install>/server/ghidraSvr console"
        # ---------------------------------------------
        # NOTE ghidra server should be configured with desired cmd-line options in
        # its server.conf:
        # ----------
        # wrapper.java.maxmemory = 16 + (32 * FileCount/10000) + (2 * ClientCount)
        # wrapper.java.maxmemory=XX   // in MB
        # ghidra.repositories.dir=/home/cls0027/ghidra_server_projects
        # <parameters>: -anonymous <ghidra.repositories.dir> OR
        #               -a0 -e0 -u <ghidra.repositories.dir>
        # ---------------------------------------------
        rc = subprocess.call(['tmux', 'new-window', '-n', 'ghidra_server', f'{ghidraSvr} console'])
        if rc == 0:
            print('Started ghidra server')
        else:
            print(f'Error starting ghidra server (return code {rc})')
    else:
        print('Ghidra already running')

def start_ghidra_server(ghidra_path:str='') -> ExpStep:
    '''
    Returns an ExpStep that checks to make sure ghidra server is running on the default port.
    If not, the ghidra server is started (as current user) in a new tmux window

    ghidra_path: Path to ghidra. May be specified here or as part of experiment params
    '''
    params = {}
    if ghidra_path:
        params[GhidraKeys.GHIDRA_INSTALL] = ghidra_path
    return ExpStep('start_ghidra_server', _start_ghidra_server, params)

def _create_shared_project(exp:'Experiment', params:Dict[str,Any], outputs:Dict[str,Any]):
    req_keys = [GhidraKeys.GHIDRA_INSTALL]

    missing_keys = set(req_keys) - params.keys()
    if missing_keys:
        raise Exception(f"Required parameters '{missing_keys}' not in params dict")

    ghidra_scripts = (Path(__file__).parent.parent/'ghidra_scripts').resolve()
    ghidra_home = Path(params[GhidraKeys.GHIDRA_INSTALL])
    analyze_headless = ghidra_home/'support'/'analyzeHeadless'  # assuming linux for now

    repo = exp.exp_folder.stem  # use the experiment folder name if not specified
    if GhidraKeys.GHIDRA_REPO in params:
        repo = params[GhidraKeys.GHIDRA_REPO]

    cmdline = [analyze_headless, '.', 'empty', '-deleteProject', '-noanalysis',
        '-scriptPath', ghidra_scripts, '-postScript', 'create_repo.py', repo
    ]

    if GhidraKeys.GHIDRA_USER in params and GhidraKeys.GHIDRA_PWD in params:
        cmdline.extend([params[GhidraKeys.GHIDRA_USER], params[GhidraKeys.GHIDRA_PWD]])

    rc = subprocess.call(cmdline)
    print(f'GHIDRA RETURN CODE = {rc}')

def create_ghidra_repo(ghidra_path:Path=None, reponame:str='', username:str='', password:str='') -> ExpStep:
    '''
    Returns an ExpStep that creates the specified shared repository
    '''
    params = {}

    if ghidra_path:
        params[GhidraKeys.GHIDRA_INSTALL] = ghidra_path
    if reponame:
        params[GhidraKeys.GHIDRA_REPO] = reponame
    if username:
        params[GhidraKeys.GHIDRA_USER] = username
    if password:
        params[GhidraKeys.GHIDRA_PWD] = password

    return ExpStep('create_ghidra_repo', _create_shared_project, params)
