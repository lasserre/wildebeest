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
    # TODO: capture output appropriately (I can use `watch wdb status` to refresh the run/job status...)
    # and log in log files for each run or job
    # TODO: define a wildebeest runstate folder (maybe exp_root/.wildebeest/runstate/run1) and
    # have each run log its state/current processing step info there (use yaml dump/load on an object?)
    # TODO: implement QUICK cmdline for printing experiment/run status and logs
        # make it BASIC, I can add to it later very easily...
    # TODO: implement rerun('postprocessing') to allow redoing updated analysis on builds
    # (see notes below)

    # TODO: create project lists, recipes in a module and advertise them with
    # entry points? (to reuse them as 'libraries' of projects/lists we can easily
    # reuse across experiments)

    recipe = ProjectRecipe('cmake',
        'git@github.com:lasserre/test-programs.git',
        [LANG_CPP, LANG_C])

    test_folder = Path('/home/cls0027/test_builds')
    proj_root = test_folder/"test-programs"
    build = ProjectBuild(proj_root, proj_root/"build", recipe)

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
    exp.run()

    # TODO: implement experiment.rerun() or runfrom() stuff using the
    # serialized output dict state
        # >> this allows me to build a bunch of stuff,
        # **CHANGE THE ANALYSIS**
        # ...and only rerun the postprocessing

        # save the runstate, output dict state in a run folder after each
        # step? (that way we could resume it)
    # dd = {
    #     'abc': 123,
    #     'experiment': exp,
    #     'driver': driver,
    #     'nested': {
    #         'config': runconfig
    #     }
    # }

    # from yaml import load, dump, Loader
    # with open('dump.yaml', 'w') as f:
    #     f.write(dump(dd))

    # with open('dump.yaml', 'r') as f:
    #     data = load(f.read(), Loader)

    import IPython; IPython.embed()

if __name__ == '__main__':
    main()
