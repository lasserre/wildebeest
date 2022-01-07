from wildebeest.buildsystemdrivers import CmakeDriver
from wildebeest import ProjectBuild

def main():
    print('In test driver!')

    # 1. put together the simplest possible makefile (and/or cmakelists.txt)
    # for my tiny C program and get that building

    #########################
    # TODO pick up here
    #########################
    # specify the project recipe here
    # then convert to a GitRepository
    # then create/convert to a ProjectBuild
    # ...and pass that to the buildsystem driver

    # ProjectBuild('/home/cls0027/')

    driver = CmakeDriver()
    driver.init()

    # TODO LIST:
    # 2. Use that with a buildsystemdriver
    # 3. Convert that to a project recipe
    # 4. Create a basic experiment using this...add the post-processing when ready
    # 5. Implement the experiment runner to manage the experiment layout
    # and kick off jobs (serially at first)
    # 6. Finish it out to get an end-to-end funcprotos experiment
    # (keep it in phd/research/funcprotos)
