from wildebeest.sourcelanguages import LANG_C, LANG_CPP
from . import CreateProjectRecipe

# this wouldn't work because raceintospace is an instance, not a callable!
# raceintospace = ProjectRecipe('cmake', 'https://github.com/raceintospace/raceintospace',
    #     source_languages=[])

game_list = [
    CreateProjectRecipe(build_system='cmake', git_remote='https://github.com/raceintospace/raceintospace',
        source_languages=[LANG_CPP, LANG_C])
]

# eventually move this into game_list ...
docker_test_list = [
    # CreateProjectRecipe(build_system='cmake', git_remote='https://github.com/superjer/tinyc.games',
    #     source_languages=[LANG_C])

    # not really a game but oh well hahaha
    CreateProjectRecipe(build_system='make', git_remote='https://github.com/orangeduck/Corange',
                        source_languages=[LANG_C])
]