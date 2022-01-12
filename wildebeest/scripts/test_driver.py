from pathlib import Path
from subprocess import run
from wildebeest.buildsystemdrivers import CmakeDriver
from wildebeest import *
from wildebeest.runconfig import RunConfig

def main():

    #########################
    # TODO pick up here
    #########################
    # TODO: define the post-processing steps for funcprotos on THIS experiment
        # 1. define a reusable ProcessingStep for finding (scraping?) the executables and their
        #    object instrumentation files (with a supplied extension) generated in the build by
        #    our "instrumenting compiler"
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

    runconfig = RunConfig()
    clangdir = Path.home()/'software'/'llvm-features-12.0.1'
    runconfig.c_options.compiler_path = clangdir/'bin'/'clang'
    runconfig.cpp_options.compiler_path = clangdir/'bin'/'clang++'

    flags = ClangFlags.load_plugin(Path.home()/'dev'/'clang-funcprotos'/'build'/'libfuncprotos.so', 'funcprotos')
    flags.append('-fuse-ld=lld')
    runconfig.c_options.compiler_flags = flags
    runconfig.cpp_options.compiler_flags = flags

    exp = Experiment('funcprotos', DefaultBuildAlgorithm(),
        projectlist=[recipe],
        runconfigs=[runconfig],
        exp_containing_folder=Path().home()/'test_builds')
    exp.algorithm.insert_after('build', ProcessingStep(
            'postprocess', lambda run, outputs: print('In post-processing!'))
        )
    # exp.run()

    import IPython; IPython.embed()

if __name__ == '__main__':
    main()
