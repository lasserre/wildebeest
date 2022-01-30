from pathlib import Path
import subprocess
from telnetlib import IP
from typing import Any, Dict

from ..algorithmstep import RunStep
from ..run import Run

from ..ghidrautil import GhidraKeys

def do_import_binary_to_ghidra(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    req_keys = [GhidraKeys.GHIDRA_INSTALL, GhidraKeys.GHIDRA_REPO]

    missing_keys = set(req_keys) - params.keys()
    if missing_keys:
        raise Exception(f"Required parameters '{missing_keys}' not in params dict")

    repo = params[GhidraKeys.GHIDRA_REPO]
    ghidra_home = Path(params[GhidraKeys.GHIDRA_INSTALL])
    analyze_headless = ghidra_home/'support'/'analyzeHeadless'  # assuming linux for now

    # TODO loop through each STRIPPED binary
    # fb = outputs['flatten_binaries'][0]

    # subprocess.call([analyze_headless, f"ghidra://localhost/{repo}/{fb.data_folder.name}",
    #     "-import", f'{fb.binary_file}', '-overwrite'])

    # TODO: strip first
    # TODO verify we have stripped it...?

    # import IPython; IPython.embed()

def ghidra_import(ghidra_path:str='') -> RunStep:
    params = {}
    if ghidra_path:
        params[GhidraKeys.GHIDRA_INSTALL] = ghidra_path
    return RunStep('ghidra_import', do_import_binary_to_ghidra, {})
