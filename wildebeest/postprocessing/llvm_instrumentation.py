'''
This includes code to help locate paths of instrumentation files using
the extensions we've added to LLVM - both Clang and the LLVM linker - for
instrumenting the compilation process and identifying object files used during
linking.
'''

from pathlib import Path
import pandas as pd
from typing import Any, Dict, List

from ..algorithmstep import RunStep
from ..run import Run

def do_find_instr_files(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    if 'find_binaries' not in outputs:
        raise Exception('Need the find_binaries step to be run first')

    if 'extensions' not in params:
        raise Exception('No instrumentation file extensions specified')

    result = {}
    lobjs = outputs['find_binaries']['linker-objects']

    for lo in lobjs:
        binary = lo.with_suffix('')
        if 'CMakeFiles' in binary.parts:
            continue    # don't include the binaries cmake builds during configure
        result[binary] = {}
        df = pd.read_csv(lo, names=['Object','Status'])
        objs = [Path(x) for x in df[df['Status']=='OK'].Object]
        for ext in params['extensions']:
            instr_files = [obj.with_suffix(f'.{ext}') for obj in objs]
            result[binary][ext] = [x for x in instr_files if x.exists()]
    return result

def find_instrumentation_files(extensions:List[str], step_name:str='find_instrumentation') -> RunStep:
    '''
    Returns a RunStep that will find instrumentation files with the
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
    return RunStep(step_name, do_find_instr_files, params={
        'extensions': list(extensions)
    })

def _rebase_linker_objects(old_exp:Path, new_exp:Path, build_folder:Path):
    '''
    Rebases all linker objects files in this build folder from the given old
    experiment path to the new experiment path. After this has been done, the
    experiment can be rerun from the 'find_binaries' step and everything should
    work using the new paths.

    This is a very specialized workaround to allow rebasing an experiment with
    linker-objects after a copy or move. Since the linker-objects files have absolute
    paths, if we simply rerun the post-build processing, we will be looking for
    object files using old absolute paths (in the absolute wrong locations).

    old_exp: Experiment folder for previous experiment location
    new_exp: Experiment folder for new experiment location
    build_folder: The build folder within which to rebase all .linker-objects files
    '''
    lobjs = list(build_folder.rglob('*.linker-objects'))

    for lo in lobjs:
        df = pd.read_csv(lo, names=['Object','Status'])

        # set this flag if we find a rebased path DNE when it used to
        # we should abort and fix it manually without messing things up
        good_objs_dne = False

        for i, row in df.iterrows():
            if row.Status == 'DNE':
                # if it DNE to begin with, don't try and rebase it
                continue
            objpath = Path(row.Object)
            # only update object paths that were within the old experiment
            if old_exp in objpath.parents:
                new_objpath = new_exp/objpath.relative_to(old_exp)
                if not new_objpath.exists():
                    print(f'Warning: new object path {new_objpath} DNE')
                    good_objs_dne = True    # this one should have been ok still
                else:
                    # verified new path exists, use it
                    df.at[i, 'Object'] = str(new_objpath)

        if good_objs_dne:
            raise Exception(f'{lo}: Found formerly-OK object file paths that DNE after rebasing. Aborting w/o file changes')

        # write rebased linker-objects
        df.to_csv(lo, header=False, index=False)

    # import IPython; IPython.embed()

def _do_find_binaries(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    lobjs = list(run.build.build_folder.rglob('*.linker-objects'))
    # remove .linker-objects to get binary name
    binaries = [x.with_suffix('') for x in lobjs]

    result = {}
    result['linker-objects'] = lobjs
    result['binaries'] = binaries
    return result

def find_binaries() -> RunStep:
    '''
    Creates a RunStep that will find binaries linked with our modified
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
    return RunStep('find_binaries', _do_find_binaries)
