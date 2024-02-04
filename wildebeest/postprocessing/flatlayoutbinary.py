import pandas as pd
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Dict, List

from ..run import Run
from ..experimentalgorithm import RunStep
from ..runconfig import recognized_opt_levels
from .llvm_instrumentation import is_cmake_generated

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
        self.debug_binary_file:Path = None  # filled out by strip_binaries
        self.stripped_binary_file:Path = None   # filled out by strip_binaries
        self.linker_objs = linker_objs
        self.data_folder:Path = run.data_folder/f'{binary_id}.{binary_file.stem}'
        self.id:int = binary_id
        self.data:Dict[str,Any] = {}
        '''
        Postprocessing steps can attach their binary-specific outputs here
        if desired. The keys should be the name of that step, and the value is
        step-specific.
        '''

def elf_has_debuginfo(elf:Path) -> bool:
    rval = subprocess.run(f'readelf -t {elf} | grep debug_info > /dev/null', shell=True).returncode
    return bool(rval == 0)

def find_binaries_in_path(build_path:Path, no_cmake:bool) -> List[Path]:
    # this finds all file that can be executed (no static libraries..)
    raw_output = subprocess.check_output(f'find {build_path} -type f -executable -print | xargs file | grep "ELF 64-bit"', shell=True).decode('utf-8')
    raw_lines = [x for x in raw_output.split('\n') if x]

    regex_results = [re.match('(.*):\s+ELF 64-bit.*', rl) for rl in raw_lines]
    elf_files = [Path(res.groups()[0]) for res in regex_results if res]

    # now verify they have debug info...
    debug_elfs = [elf for elf in elf_files if elf_has_debuginfo(elf)]

    if no_cmake:
        debug_elfs = [x for x in debug_elfs if not is_cmake_generated(Path(x))]

    for elf in debug_elfs:
        print(f'File {Path(elf)} has debug info')

    # import IPython; IPython.embed()
    return debug_elfs

def find_binaries_main():
    import argparse
    p = argparse.ArgumentParser(description='Find executables in the given build folder')
    p.add_argument('build_folder')
    p.add_argument('--no-cmake', help='Exclude cmake-generated binaries', action='store_true')
    args = p.parse_args()
    find_binaries_in_path(Path(args.build_folder), bool(args.no_cmake))
    return 0

def calc_percent_cpp_names_in_binary(elf:Path) -> float:
    total_syms = subprocess.check_output(f'nm {elf} | wc -l', shell=True).decode('utf-8')
    cpp_syms = subprocess.check_output(f'nm {elf} | c++filt | grep "::" | wc -l', shell=True).decode('utf-8')

    if int(total_syms) > 0:
        return int(cpp_syms)/int(total_syms)
    return -1

def is_cpp_debug_binary(elf:Path, cppnames_thresh:float=0.65) -> bool:
    '''
    cppnames_thresh: Threshold for % of C++ symbol names in the debug binary which
                     flag a binary as being a "C++ binary"
    '''
    percent_cpp = calc_percent_cpp_names_in_binary(elf)
    if percent_cpp > -1:
        print(f'{percent_cpp*100:.2f}% of symbols are C++ syms in {elf.name}')
        return percent_cpp > cppnames_thresh
    else:
        print(f'No symbols in binary {elf}')
        return False

def _do_find_binaries(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    debug_bins = find_binaries_in_path(run.build.build_folder, no_cmake=True)
    good_bins = [x for x in debug_bins if validate_optimization_level(run, x)]

    return {
        'binaries': good_bins
    }

def find_binaries() -> RunStep:
    '''
    Creates a RunStep that will find binaries that are 64-bit ELF files
    and contain a debug_info section

    Outputs
    -------
    The output of this step is a dictionary with this format:
    {
        'binaries': [ list of corresponding binary paths ],
    }
    '''
    return RunStep('find_binaries', _do_find_binaries)

def _do_flatten_binaries(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    if 'find_binaries' not in outputs:
        raise Exception('Need the find_binaries step to be run first')

    binaries = outputs['find_binaries']['binaries']
    bdict = {}
    for i, b in enumerate(binaries):
        lobj = b.with_suffix('.linker-objects')
        lobj = lobj if lobj.exists() else None
        bdict[i] = FlatLayoutBinary(i, b, lobj, run)
        bdict[i].data['percent_cpp'] = calc_percent_cpp_names_in_binary(b)

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

def validate_optimization_level(run:Run, binfile:Path) -> bool:
    '''
    Validate that no other optimization levels appear in DW_AT_producer strings in the binary's DWARF info

    Returns True if binary matches desired level, False otherwise
    '''
    dw_at_producer = subprocess.check_output(f'readelf --debug-dump=info {binfile} | grep DW_AT_producer', shell=True).decode('utf-8')
    other_levels = [x for x in recognized_opt_levels() if x != run.config.opt_level]

    # NOTE: remember, if multiple flags appear then the last one wins. But right now just validate
    # that no other flags appear. If we can't avoid multiple in the future, we can add logic to
    # validate that our flag always appears last in the multiple flags case

    found_others = re.match(f'.*({"|".join(other_levels)}).*', dw_at_producer)
    if found_others:
        print(f'{binfile} compiled with unwanted optimization level (opt_level={run.config.opt_level}). Found {found_others.groups()[0]}')

    return bool(not found_others)

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
        subprocess.call([run.config.strip_executable, '-s', stripped])
        fb.data['strip_binaries'] = stripped
        fb.data['debug_binaries'] = origcopy
        fb.debug_binary_file = origcopy
        fb.stripped_binary_file = stripped

    # import IPython; IPython.embed()

def strip_binaries() -> RunStep:
    return RunStep('strip_binaries', _do_strip_binaries, run_in_docker=True)
