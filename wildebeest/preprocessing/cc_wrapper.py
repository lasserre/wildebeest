import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import List, Dict, Any

from .. import RunStep
from ..run import Run, RunConfig
from ..runconfig import recognized_opt_levels
from ..utils import env

def get_cc_wrapper_path() -> Path:
    return Path(subprocess.check_output(['which', 'cc_wrapper']).decode('utf-8').strip())

def get_cxx_wrapper_path() -> Path:
    return Path(subprocess.check_output(['which', 'cxx_wrapper']).decode('utf-8').strip())

# actually doing this directly when we create the recipe docker image, but saving
# this function in case we need to do it within docker later
def uninstall_cc_wrapper():
    wrapper_bin = Path('/wrapper_bin')
    if wrapper_bin.exists():
        shutil.rmtree(wrapper_bin)
    subprocess.run(['hash', '-r'], shell=True)  # apparently bash caches program locations... https://unix.stackexchange.com/a/91176

def do_install_cc_wrapper(run:Run, params:Dict[str,Any], outputs:Dict[str,Any]):
    if run.build.recipe.no_cc_wrapper:
        print(f'Skipping install_cc_wrapper for recipe {run.build.recipe.name}')
        return

    # find full path to target compiler
    c_compiler_path = Path(subprocess.check_output(['which', run.config.c_options.compiler_path]).decode('utf-8').strip())
    cpp_compiler_path = Path(subprocess.check_output(['which', run.config.cpp_options.compiler_path]).decode('utf-8').strip())

    cc_link = Path('/wrapper_bin')/c_compiler_path.name
    cxx_link = Path('/wrapper_bin')/cpp_compiler_path.name

    # create symlink to cc_wrapper named <target_compiler> in /wrapper_bin
    subprocess.run(['ln', '-s', get_cc_wrapper_path(), cc_link])
    subprocess.run(['ln', '-s', get_cxx_wrapper_path(), cxx_link])
    subprocess.run(['hash', '-r'], shell=True)  # apparently bash caches program locations... https://unix.stackexchange.com/a/91176

    # allow cc_wrapper to find full path to target compiler for actual invocation later
    # NOTE: we have a unique container name (from docker run --name) for each run. I don't think
    # the files (not mounted) will persist...CHECK THIS
    # - if so, I can write the full path to a file at ~/compiler_full_path
    with open(Path.home()/'cc_path.txt', 'w') as f:
        f.write(str(c_compiler_path))
    with open(Path.home()/'cxx_path.txt', 'w') as f:
        f.write(str(cpp_compiler_path))

    # DEBUGGING
    print(subprocess.check_output(['ls', '-al', '/wrapper_bin']).decode('utf-8'))

def install_cc_wrapper() -> RunStep:
    return RunStep('install_cc_wrapper', do_install_cc_wrapper, run_in_docker=True)

def optflag_in_string(s:str) -> bool:
    return any([x for x in recognized_opt_levels() if x in s])

def filter_optimization_args(argv:List[str]) -> List[str]:
    return [x for x in argv if x not in recognized_opt_levels()]

def main():
    '''
    From GCC docs: https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html

    "If you use multiple -O options, with or without level numbers, the last such option is the one that is effective."

    Instead of trying to ensure we are LAST, we just eat everything and replace with the one we want :)
    '''
    # we ASSUME we are called via the symlink - our symlink name will match
    # the name of our target compiler
    symlink_path = Path(sys.argv[0])
    opt_level = os.environ['OPT_LEVEL'] if 'OPT_LEVEL' in os.environ else '-O0'

    # handle cc vs cxx compiler
    with open(Path.home()/'cxx_path.txt', 'r') as f:
        cxx_compiler = Path(f.readlines()[0].strip())
    with open(Path.home()/'cc_path.txt', 'r') as f:
        c_compiler = Path(f.readlines()[0].strip())

    is_cxx = symlink_path.name == cxx_compiler.name
    compiler = str(cxx_compiler) if is_cxx else str(c_compiler)
    FLAGS_VAR = 'CXXFLAGS' if is_cxx else 'CFLAGS'

    filtered_flags = ''
    if FLAGS_VAR in os.environ:
        filtered_flags = ' '.join(filter_optimization_args(os.environ[FLAGS_VAR].split()))

    compiler_args = filter_optimization_args(sys.argv[1:])
    # put the desired optimization level at the front
    # (for C++, -lstdc++ MUST go last!! https://stackoverflow.com/a/6045967)
    compiler_args.insert(0, opt_level)

    # NOTE: this did not work because some paths have '@' symbol in it
    # -> if we want to prevent options getting past us via "gcc @file" then
    # we can come back and re-address, but I haven't actually seen this be an
    # issue yet
    # if any(['@' in x for x in [*compiler_args, *filtered_flags]]):
    #     raise Exception(f'Found @ arguments: {[*compiler_args, "CFLAGS...", *filtered_flags]}')

    envdict = {FLAGS_VAR: filtered_flags} if filtered_flags else {}

    # print(f'Using optimization level {opt_level}')
    # print(f'Using compiler at: {compiler}')
    # print(f'Original {FLAGS_VAR}: {os.environ[FLAGS_VAR]}', file=sys.stderr)
    # print(f'Filtered {FLAGS_VAR}: {filtered_flags}', file=sys.stderr)
    # print(f'Called with: {sys.argv}', file=sys.stderr)
    # print(f'Filtered to: {compiler_args}', file=sys.stderr)
    converted_args = []
    for x in compiler_args:
        if '"' in x:
            print(f'Found argument {x} with quotes', file=sys.stderr, flush=True)
            converted_args.append(x.replace('"', r'\"'))    # escape quotes
        else:
            converted_args.append(x)

    with env(envdict):
        # print(f'sys.arv was: {" ".join(sys.argv)}', flush=True)
        # print(f'sys.arv was: {" ".join(sys.argv)}', file=sys.stderr, flush=True)
        # print(f'CALLING COMPILER: {" ".join([compiler, *compiler_args])}', flush=True)
        # print(f'CALLING COMPILER: {" ".join([compiler, *compiler_args])}', file=sys.stderr, flush=True)
        return subprocess.run(' '.join([compiler, *compiler_args]), shell=True).returncode
