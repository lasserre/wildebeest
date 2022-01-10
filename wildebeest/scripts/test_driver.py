from pathlib import Path
from subprocess import run
from wildebeest.buildsystemdrivers import CmakeDriver
from wildebeest import *
from wildebeest.runconfig import RunConfig

def main():

    #########################
    # TODO pick up here
    #########################
    # specify the project recipe here
        # it's ok to have configure, build, clean, etc. steps be defined for
        # normal usage (even though the algorithm is configurable):

        # >> have Experiment() constructor default to the DefaultBuildAlgorithm
        #
        # recipe.post_configure = myproject_configure
        #

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

    driver = CmakeDriver()

    # build.init()
    # driver.configure(runconfig, build)
    # driver.build(runconfig, build, 2)

    #build.destroy(True)

    # TODO: re-create an experiment instance here once I've finished implementing
    # experiment.run()
    # ----------------
    # exp = Experiment('funcprotos', DefaultBuildAlgorithm(), runs=[])
    # exp.algorithm.insert_after('build', ProcessingStep('postprocess'))
    # exp.run()

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

    # TODO LIST:
    # 3. Convert this to an experiment algorithm (DefaultBuildAlgorithm + custom stuff)
        # TODO: define default build algorithm
        # TODO: implement the postprocessing for funcprotos!
    # 4. Create a basic experiment using this...add the post-processing when ready
    # 5. Implement the experiment runner to manage the experiment layout
    # and kick off jobs (serially at first)
    # 6. Finish it out to get an end-to-end funcprotos experiment
    # (keep it in phd/research/funcprotos)

if __name__ == '__main__':
    main()
