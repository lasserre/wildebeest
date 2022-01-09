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

    # TODO: use my compiler...
    # export CXX="$Clang_DIR/bin/clang++"
    # export CC="$Clang_DIR/bin/clang"
    # export CXXFLAGS="-Xclang -load -Xclang ~/dev/clang-funcprotos/build/libfuncprotos.so -Xclang -add-plugin -Xclang funcprotos -fuse-ld=lld"
    # export CFLAGS=$CXXFLAGS
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

    build.init()
    driver.configure(runconfig, build)
    driver.build(runconfig, build, 2)
    #build.destroy(True)

    import IPython; IPython.embed()

    # TODO LIST:
    # 3. Convert this to an experiment algorithm (DefaultBuildAlgorithm + custom stuff)
    # 4. Create a basic experiment using this...add the post-processing when ready
    # 5. Implement the experiment runner to manage the experiment layout
    # and kick off jobs (serially at first)
    # 6. Finish it out to get an end-to-end funcprotos experiment
    # (keep it in phd/research/funcprotos)

if __name__ == '__main__':
    main()
