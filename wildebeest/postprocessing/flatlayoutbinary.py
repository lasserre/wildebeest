import pandas as pd
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict

from ..run import Run
from ..experimentalgorithm import RunStep

class FlatLayoutBinary:
    def __init__(self, binary_id:int, binary_file:Path, linker_objs:Path,
                run:Run) -> None:
        '''
        binary_id: The zero-based id generated for this binary
        binary_file: Path to the original binary file in the build folder
        linker_objs: Path to the original .linker-objects file for this binary
        run: The current Run, whose data folder will be the parent folder of
             this binary's data folder
        '''
        self.binary_file:Path = binary_file
        self.linker_objs = linker_objs
        self.data_folder:Path = run.data_folder/f'{binary_id}.{binary_file.stem}'
        self.id:int = binary_id
        self.data:Dict[str,Any] = {}
        '''
        Postprocessing steps can attach their binary-specific outputs here
        if desired. The keys should be the name of that step, and the value is
        step-specific.
        '''

def _do_flatten_binaries(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    if 'find_binaries' not in outputs:
        raise Exception('Need the find_binaries step to be run first')

    binaries = outputs['find_binaries']['binaries']
    bdict = {}
    for i, b in enumerate(binaries):
        lobj = b.with_suffix('.linker-objects')
        bdict[i] = FlatLayoutBinary(i, b, lobj, run)

    df = pd.DataFrame([vars(fb) for fb in bdict.values()])
    df.to_csv(run.data_folder/'flat_layout.csv', index=False)

    for fb in bdict.values():
        fb.data_folder.mkdir(parents=True, exist_ok=True)

    del outputs['find_binaries']
    return bdict

def flatten_binaries() -> RunStep:
    '''
    Creates a RunStep that will create a flat subfolder structure in the Run's
    data folder for each of the binaries located by find_binaries (which is a required
    previous step).

    The purpose is to avoid both 1) name conflicts for projects that build multiple
    binaries of the same name in different folders, and 2) a confusing multi-level
    layout that would result if we simply matched the relative path of each binary
    in the build folder (which could be deep and could be unnecessarily hard to locate
    outputs).

    Instead, we go through each binary file and generate an ID starting from zero.
    Then a binary data folder is created in the run's data folder, where all of
    that binary's analysis outputs will be placed. This mapping is saved to the data
    folder as a csv for reference, but the idea is to save data outputs within the
    binaryN folders using the original binary name (e.g. binary3/myprogram.csv),
    so hopefully it will be straightforward to locate binaries of interest
    (using grep or tree -L 2) without consulting the lookup each time.

    Outputs
    -------
    This step removes the (required) previous output of find_binaries, and returns
    an output dictionary that transforms the find_binaries 'binaries' list into
    a dictionary mapping binary ID to its FlatLayoutBinary instance:
    {
        maps binary ID -> FlatLayoutBinary instance for each binary, which
                          includes binary, data folder, and linker-objects paths
    }
    '''
    return RunStep('flatten_binaries', _do_flatten_binaries)

def _do_strip_binaries(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    # STRIP:
    # -------
    # cp program data_folder/program
    # cp data_folder/program data_folder/program.debug  # (optional) copy debug info version local
    # strip -s data_folder/program  # strips program in-place

    if 'flatten_binaries' not in outputs:
        raise Exception('Expecting flatten_binaries to be run first')

    for _, fb in outputs['flatten_binaries'].items():
        fb:FlatLayoutBinary

        stripped = fb.data_folder/f'{fb.binary_file.name}'
        # origcopy is optional...
        origcopy = stripped.with_suffix('.debug')
        shutil.copy(fb.binary_file, origcopy)
        shutil.copy(fb.binary_file, stripped)
        subprocess.call(['strip', '-s', stripped])
        fb.data['strip_binaries'] = stripped

    # import IPython; IPython.embed()

def strip_binaries() -> RunStep:
    return RunStep('strip_binaries', _do_strip_binaries)
