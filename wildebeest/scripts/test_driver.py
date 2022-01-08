from pathlib import Path
from wildebeest.buildsystemdrivers import CmakeDriver
from wildebeest import ProjectBuild
from wildebeest.projectrecipe import ProjectRecipe
from wildebeest.runconfig import RunConfig

def main():
    print('In test driver!')

    # 1. put together the simplest possible makefile (and/or cmakelists.txt)
    # for my tiny C program and get that building

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

    # ProjectBuild('/home/cls0027/')
    recipe = ProjectRecipe('cmake', 'git@github.com:lasserre/test-programs.git',
            git_head='HEAD~2')

    test_folder = Path('/home/cls0027/test_builds')
    proj_root = test_folder/"test-programs"
    build = ProjectBuild(proj_root, proj_root/"build", recipe)

    # TODO customize the compiler settings here...
    runconfig = RunConfig()

    # TODO implement with no customizations first, then use the runconfig
    driver = CmakeDriver()

    build.init()

    import IPython; IPython.embed()

    # build.init()
    # driver.configure(runconfig, build)
    # driver.build(build, 2)
    # driver.clean
    # import IPython; IPython.embed()

    # TODO LIST:
    # 3. Convert this to an experiment algorithm (DefaultBuildAlgorithm + custom stuff)
    # 4. Create a basic experiment using this...add the post-processing when ready
    # 5. Implement the experiment runner to manage the experiment layout
    # and kick off jobs (serially at first)
    # 6. Finish it out to get an end-to-end funcprotos experiment
    # (keep it in phd/research/funcprotos)

if __name__ == '__main__':
    main()
