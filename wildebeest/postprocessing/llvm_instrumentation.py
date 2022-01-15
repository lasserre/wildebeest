'''
This includes code to help locate paths of instrumentation files using
the extensions we've added to LLVM - both Clang and the LLVM linker - for
instrumenting the compilation process and identifying object files used during
linking.
'''

from pathlib import Path
import pandas as pd
from typing import Any, Dict, List

from ..experiment import ProcessingStep, Run

def find_instrumentation_files(extensions:List[str], step_name:str='find_instrumentation') -> ProcessingStep:
    '''
    Returns a ProcessingStep that will find instrumentation files with the
    given extensions

    Requirements
    ------------
    The find_binaries step must run first to locate all of the binaries and
    linker-objects files

    Outputs
    -------
    The output of this step is a dictionary with this format:
    {
        binary_path[Path]: {
            extension[str]: [ paths to instrumentation files ],
        },
    }
    where there may be multiple binary paths, each with multiple extensions
    '''
    def do_find_instr_files(run:Run, outputs:Dict[str,Any]):
        if 'find_binaries' not in outputs:
            raise Exception('Need the find_binaries step to be run first')

        result = {}
        lobjs = outputs['find_binaries']['linker-objects']

        for lo in lobjs:
            binary = lo.with_suffix('')
            result[binary] = {}
            df = pd.read_csv(lo, names=['Object','Status'])
            objs = [Path(x) for x in df[df['Status']=='OK'].Object]
            for ext in extensions:
                instr_files = [obj.with_suffix(f'.{ext}') for obj in objs]
                result[binary][ext] = [x for x in instr_files if x.exists()]
        return result

    return ProcessingStep(step_name, do_find_instr_files)

def _do_find_binaries(run:Run, outputs:Dict[str,Any]):
    lobjs = list(run.build.build_folder.rglob('*.linker-objects'))
    # remove .linker-objects to get binary name
    binaries = [x.with_suffix('') for x in lobjs]

    result = {}
    result['linker-objects'] = lobjs
    result['binaries'] = binaries
    return result

def find_binaries() -> ProcessingStep:
    '''
    Creates a ProcessingStep that will find binaries linked with our modified
    LLVM linker. Each such binary will have a .linker-objects file output next
    to it, which is how we can locate them.

    Outputs
    -------
    The output of this step is a dictionary with this format:
    {
        'linker-objects': [ list of linker object paths ],
        'binaries': [ list of corresponding binary paths ],
    }
    '''
    return ProcessingStep('find_binaries', _do_find_binaries)
