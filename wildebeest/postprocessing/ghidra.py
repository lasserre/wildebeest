import json
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Callable

from ..algorithmstep import RunStep
from ..run import Run
from ..ghidrautil import GhidraKeys
from .flatlayoutbinary import FlatLayoutBinary
from ..utils import env

def do_import_binary_to_ghidra(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    req_keys = [GhidraKeys.GHIDRA_INSTALL, GhidraKeys.GHIDRA_REPO, 'binary_key']

    missing_keys = set(req_keys) - params.keys()
    if missing_keys:
        raise Exception(f"Required parameters '{missing_keys}' not in params dict")

    binary_key = params['binary_key']
    postscript:Path = params['postscript'] if 'postscript' in params else None
    repo = params[GhidraKeys.GHIDRA_REPO]
    ghidra_home = Path(params[GhidraKeys.GHIDRA_INSTALL])
    analyze_headless = ghidra_home/'support'/'analyzeHeadless'  # assuming linux for now

    for bid, fb in outputs['flatten_binaries'].items():
        fb:FlatLayoutBinary
        binary = fb.data[binary_key] if binary_key else fb.binary_file

        # CLS: right now I can't find a way to control the filename that a binary is
        # imported as into ghidra, other than creating a link such that the filename
        # is what I want it to be in ghidra :P
        debug_suffix = '.debug' if binary.name.endswith('.debug') else ''
        bin_symlink = fb.data_folder/f'{fb.data_folder.name}{debug_suffix}'
        if not bin_symlink.exists():
            bin_symlink.symlink_to(binary)

        ghidra_folder = f'run{run.number}.{run.config.name}.{run.build.recipe.name}'
        analyze_cmd_BASE = [analyze_headless, f"ghidra://localhost/{repo}/{ghidra_folder}"]

        # CLS: try doing this in 2 steps to avoid "Function @ 0x... not fully decompiled
        # (no structure present)" error I was getting a ton of...
        import_cmd = [*analyze_cmd_BASE, "-import", f'{bin_symlink}', '-overwrite']
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

        if debug_suffix:
            ast_config = fb.data_folder/'ghidra_ast.debug.json'
            ast_folder = fb.data_folder/'ast_dumps'/'debug'
            fb.data['debug_asts'] = ast_folder
        else:
            ast_config = fb.data_folder/'ghidra_ast.json'
            ast_folder = fb.data_folder/'ast_dumps'/'stripped'
            fb.data['stripped_asts'] = ast_folder
        ast_folder.mkdir(exist_ok=True, parents=True)     # folder has to exist or we don't get output!

        # import the binary first, run autoanalysis
        rcode = subprocess.call(import_cmd)
        if rcode != 0:
            raise Exception(f'Ghidra import failed with return code {rcode}')

        # write AST config file, process the imported binary
        with open(ast_config, 'w') as f:
            f.write(json.dumps({'output_folder': str(ast_folder)}))

        with env({'GHIDRA_AST_CONFIG_FILE': str(ast_config)}):
            rcode = subprocess.call(analyze_cmd)
            if rcode != 0:
                raise Exception(f'Ghidra postscript processing failed with return code {rcode}')

    # import IPython; IPython.embed()

def ghidra_import(binary_key:str='', postscript:Path=None,
    get_postscriptargs:Callable[[FlatLayoutBinary], List[str]]=None,
    ghidra_path:str='') -> RunStep:
    '''
    binary_key: Optionally specifies a key for FlatLayoutBinary.data that ghidra_import
                should use to retrieve a path to the modified/processed binary instead
                of the original (for each FlatLayoutBinary in flatten_binaries).
                If not specified, the original binary file will be imported
    '''
    params = {
        'binary_key': binary_key
    }
    if ghidra_path:
        params[GhidraKeys.GHIDRA_INSTALL] = ghidra_path
    if postscript:
        params['postscript'] = postscript
    if get_postscriptargs:
        params['get_postscriptargs'] = get_postscriptargs
    return RunStep(f'ghidra_import_{binary_key}', do_import_binary_to_ghidra, params)
