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
    if 'flatten_binaries' not in outputs:
        raise Exception('Need the flatten_binaries step to be run first')

    if 'extensions' not in params:
        raise Exception('No instrumentation file extensions specified')

    for fb in outputs['flatten_binaries'].values():
        lo = fb.linker_objs
        binary_instr = {}
        df = pd.read_csv(lo, names=['Object','Status'])
        objs = [Path(x) for x in df[df['Status']=='OK'].Object]
        for ext in params['extensions']:
            instr_files = [obj.with_suffix(f'.{ext}') for obj in objs]
            binary_instr[ext] = [x for x in instr_files if x.exists()]
        fb.data['find_instrumentation'] = binary_instr
    return {}

def find_instrumentation_files(extensions:List[str], step_name:str='find_instrumentation') -> RunStep:
    '''
    Returns a RunStep that will find instrumentation files with the
    given extensions

    Requirements
    ------------
    The flatten_binaries step must run first to locate all of the binaries and
    linker-objects files and convert them into FlatLayoutBinary instances

    Outputs
    -------
    This step attaches a dictionary with the following format to each FlatLayoutBinary's
    data dict:
    binary.data['find_instrumentation'] = {
        extension[str]: [ paths to instrumentation files ],
    }
    where there may be multiple extensions.
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

def is_cmake_generated(binary:Path) -> bool:
    '''
    True if the binary path appears to be a binary generated by cmake, and
    not one built from project source code
    '''
    return 'CMakeFiles' in binary.parts and binary.stem == 'a.out'

def _do_find_binaries(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    lobjs = list(run.build.build_folder.rglob('*.linker-objects'))
    lobjs = [l for l in lobjs if not is_cmake_generated(l)]

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
