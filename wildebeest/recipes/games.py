from wildebeest.sourcelanguages import LANG_C, LANG_CPP
from . import CreateProjectRecipe

# raceintospace = ProjectRecipe('cmake', 'https://github.com/raceintospace/raceintospace',
    #     source_languages=[])

game_list = [
    CreateProjectRecipe(build_system='cmake', git_remote='https://github.com/raceintospace/raceintospace',
        source_languages=[LANG_CPP, LANG_C])
]
