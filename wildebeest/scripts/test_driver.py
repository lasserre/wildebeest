from pathlib import Path
from subprocess import run
from wildebeest.buildsystemdrivers import CmakeDriver
from wildebeest import *
from wildebeest.runconfig import RunConfig
from wildebeest.postprocessing import *

def main():

    #########################
    # TODO pick up here (when done below)
    #########################
    # TODO: define the post-processing steps for funcprotos on THIS experiment
    # TODO: capture output appropriately (I can use `watch wdb status` to refresh the run/job status...)
    # and log in log files for each run or job
    # TODO: implement QUICK cmdline for printing experiment/run status and logs
        # make it BASIC, I can add to it later very easily...
        # REMEMBER to kick off long jobs with nohup or from within tmux!

    # TODO: create project lists, recipes in a module and advertise them with
    # entry points? (to reuse them as 'libraries' of projects/lists we can easily
    # reuse across experiments)

    recipe = ProjectRecipe('cmake',
        'git@github.com:lasserre/test-programs.git',
        [LANG_CPP, LANG_C])

    rc = RunConfig()
    clangdir = Path.home()/'software'/'llvm-features-12.0.1'
    rc.c_options.compiler_path = clangdir/'bin'/'clang'
    rc.cpp_options.compiler_path = clangdir/'bin'/'clang++'

    flags = ClangFlags.load_plugin(Path.home()/'dev'/'clang-funcprotos'/'build'/'libfuncprotos.so', 'funcprotos')
    flags.append('-fuse-ld=lld')
    rc.c_options.compiler_flags.extend(flags)
    rc.c_options.enable_debug_info()
    # copy C options for C++
    rc.cpp_options.compiler_flags = list(rc.c_options.compiler_flags)

    # 1. "Build" executables to extract function prototypes using Clang `funcprotos` plugin
        # [1.2] Build debug-enabled executables using target compiler (if different from Clang used in #1)
    # 2. Extract function addresses from "debug-enabled" target binaries
    # 3. Combine the two to generate (address, function prototype) pairs. These are the labels for our data.
    # 4. Strip the executables, and supply the stripped versions to ghidra
    # 5. Extract ghidra's function prototypes for all functions in the stripped binaries
    #     > - If it's a problem, we could even help ghidra along by manually ensuring functions
    #     > are defined at each address at which we know a function to exist
    # 6. We should now have a full dataset: (address, true prototype, ghidra prototype)
    # 7. Analyze results (compute similarity metric, further analysis)

    def generate_labels(run:Run, outputs:Dict[str,Any]):
        # 2. Extract function addresses from "debug-enabled" target binaries
        # 3. Combine with .funcprotos to generate (address, function prototype) pairs. These are the labels for our data.
        if 'find_instrumentation' not in outputs:
            raise Exception('find_instrumentation output is not present')

        instr = outputs['find_instrumentation']
        for binary, extdict in instr.items():
            if 'funcprotos' in extdict:
                fp_files = extdict['funcprotos']
                print(fp_files)
                # ------------------
                # TODO: pick up here
                # ------------------
                # TODO need to define the data/ output folder for this run
                # TODO
                # 1. run python script to pull addresses from debug binaries
                # 2. combine with fp_files here -> dump result in data folder

        import IPython; IPython.embed()

    exp = Experiment('funcprotos', DefaultBuildAlgorithm(),
        projectlist=[recipe],
        runconfigs=[rc],
        exp_containing_folder=Path().home()/'test_builds')
    exp.algorithm.steps.append(find_binaries())
    exp.algorithm.steps.append(find_instrumentation_files(['funcprotos']))
    exp.algorithm.steps.append(ProcessingStep('labels', generate_labels))
    # exp.run()
    exp.rerun('find_binaries')

if __name__ == '__main__':
    main()
