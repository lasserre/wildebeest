from pathlib import Path
from typing import Any, Dict

class GhidraKeys:
    GHIDRA_INSTALL = 'GHIDRA_INSTALL'
    GHIDRA_USER = 'GHIDRA_USER'
    GHIDRA_PWD = 'GHIDRA_PWD'
    GHIDRA_REPO = 'GHIDRA_REPO'

def get_ghidra_repo(params:Dict[str,Any], exp_folder:Path):
    '''
    Returns the ghidra repo value that should be used based on the experiment and
    parameters
    '''
    repo = exp_folder.stem  # use the experiment folder name if not specified
    if GhidraKeys.GHIDRA_REPO in params:
        repo = params[GhidraKeys.GHIDRA_REPO]
    return repo
