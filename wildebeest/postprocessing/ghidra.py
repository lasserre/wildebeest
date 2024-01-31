import json
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Callable

from ..algorithmstep import RunStep
from ..run import Run
from ..ghidrautil import GhidraKeys
from .flatlayoutbinary import FlatLayoutBinary
from ..utils import env

def get_binary_symlink_name(fb:FlatLayoutBinary, binary:Path) -> Path:
    # CLS: right now I can't find a way to control the filename that a binary is
    # imported as into ghidra, other than creating a link such that the filename
    # is what I want it to be in ghidra :P
    debug_suffix = '.debug' if binary.name.endswith('.debug') else ''
    return fb.data_folder/f'{fb.data_folder.name}{debug_suffix}'

def get_ghidra_folder_for_run(run:Run) -> str:
    return f'/run{run.number}.{run.config.name}.{run.build.recipe.name}'

def get_analyze_headless_cmd_BASE(ghidra_home:str, repo:str, ghidra_folder:str):
    analyze_headless = ghidra_home/'support'/'analyzeHeadless'  # assuming linux for now
    return [analyze_headless, f"ghidra://localhost/{repo}{ghidra_folder}"]

def do_import_binary_to_ghidra(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    req_keys = [GhidraKeys.GHIDRA_INSTALL, GhidraKeys.GHIDRA_REPO]

    missing_keys = set(req_keys) - params.keys()
    if missing_keys:
        raise Exception(f"Required parameters '{missing_keys}' not in params dict")

    debug_binaries = params['debug_binaries']
    prescript:Path = params['prescript'] if 'prescript' in params else None
    postscript:Path = params['postscript'] if 'postscript' in params else None
    repo = params[GhidraKeys.GHIDRA_REPO]
    ghidra_home = Path(params[GhidraKeys.GHIDRA_INSTALL])

    for bid, fb in outputs['flatten_binaries'].items():
        fb:FlatLayoutBinary
        binary = fb.debug_binary_file if debug_binaries else fb.stripped_binary_file
        bin_symlink = get_binary_symlink_name(fb, binary)
        if not bin_symlink.exists():
            bin_symlink.symlink_to(binary)

        ghidra_folder = get_ghidra_folder_for_run(run)
        analyze_cmd_BASE = get_analyze_headless_cmd_BASE(ghidra_home, repo, ghidra_folder)

        # CLS: try doing this in 2 steps to avoid "Function @ 0x... not fully decompiled
        # (no structure present)" error I was getting a ton of...
        import_cmd = [*analyze_cmd_BASE, "-import", f'{bin_symlink}', '-overwrite']

        if prescript:
            import_cmd.extend([ '-scriptPath', prescript.parent,
                                '-preScript', prescript.name])

        analyze_cmd = []

        if postscript:
            args = []
            if 'get_postscriptargs' in params:
                args = params['get_postscriptargs'](fb)
            scriptdir = postscript.parent
            analyze_cmd = [*analyze_cmd_BASE,
                           '-process', f'{bin_symlink.name}', '-noanalysis',
                           '-scriptPath', scriptdir,
                           '-postScript', postscript.name, *args]

        # ------------------------------------------------------
        # import the binary first, run prescript & autoanalysis
        # ------------------------------------------------------
        rcode = subprocess.call(import_cmd)
        if rcode != 0:
            raise Exception(f'Ghidra import failed with return code {rcode}')

        # ------------------------------------------------------
        # now run post-processing via postscript
        # ------------------------------------------------------
        if analyze_cmd:
            rcode = subprocess.call(analyze_cmd)
            if rcode != 0:
                raise Exception(f'Ghidra postscript processing failed with return code {rcode}')

    # import IPython; IPython.embed()

def ghidra_import(debug:bool, postscript:Path=None,
    get_postscriptargs:Callable[[FlatLayoutBinary], List[str]]=None,
    ghidra_path:str='', prescript:Path=None) -> RunStep:
    '''
    debug_binaries: import debug binaries if set, otherwise import stripped binaries
    '''
    params = {
        'debug_binaries': debug
    }
    if ghidra_path:
        params[GhidraKeys.GHIDRA_INSTALL] = ghidra_path
    if postscript:
        params['postscript'] = postscript
    if get_postscriptargs:
        params['get_postscriptargs'] = get_postscriptargs
    if prescript:
        params['prescript'] = prescript
    return RunStep(f'ghidra_import_{"debug" if debug else "strip"}', do_import_binary_to_ghidra, params)
