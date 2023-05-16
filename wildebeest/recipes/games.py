from wildebeest.sourcelanguages import LANG_C, LANG_CPP
from . import CreateProjectRecipe
from .. import ProjectList
from typing import List

# this wouldn't work because raceintospace is an instance, not a callable!
# raceintospace = ProjectRecipe('cmake', 'https://github.com/raceintospace/raceintospace',
    #     source_languages=[])

game_list = [
    CreateProjectRecipe(build_system='cmake', git_remote='https://github.com/raceintospace/raceintospace',
        source_languages=[LANG_CPP, LANG_C])
]

# eventually move this into game_list ...
docker_tests = [
    # CreateProjectRecipe(build_system='cmake', git_remote='https://github.com/superjer/tinyc.games',
    #     source_languages=[LANG_C])

    # not really a game but oh well hahaha
    # CreateProjectRecipe(build_system='make', git_remote='https://github.com/orangeduck/Corange',
    #                     source_languages=[LANG_C])

    CreateProjectRecipe(build_system='cmake', git_remote='https://github.com/tek256/astera.git',
        source_languages=[LANG_C],
        apt_deps=['mesa-common-dev', 'libx11-dev', 'libxrandr-dev', 'libxi-dev', 'xorg-dev',
            'libgl1-mesa-dev', 'libglu1-mesa-dev', 'libopenal-dev'
        ]
    )
]

def create_test_list() -> List[str]:
    return [
        'astera'
    ]

docker_test_list = ProjectList('docker_test_list', create_test_list)