from wildebeest.sourcelanguages import LANG_C, LANG_CPP
from . import CreateProjectRecipe
from .. import ProjectList
from ..projectrecipe import BuildStepOptions
from typing import List

# this wouldn't work because raceintospace is an instance, not a callable!
# raceintospace = ProjectRecipe('cmake', 'https://github.com/raceintospace/raceintospace',
    #     source_languages=[])

cpp_game_recipes = [
    # CLS: don't want to include C++ right now
    CreateProjectRecipe(build_system='cmake', git_remote='https://github.com/raceintospace/raceintospace',
        # git_head='288c36e',     # arbitrary commit that I think used to work?
        git_head='v.2.0beta',
        source_languages=[LANG_CPP, LANG_C],
        apt_deps=['cmake', 'libsdl1.2-dev', 'libboost-dev', 'libpng-dev', 'libjsoncpp-dev', 'libogg-dev',
            'libvorbis-dev', 'libtheora-dev', 'libprotobuf-dev', 'protobuf-compiler', 'build-essential']
    ),
]

c_game_recipes = [
    CreateProjectRecipe(build_system='cmake', git_remote='https://github.com/tek256/astera.git',
        source_languages=[LANG_C],
        configure_options=BuildStepOptions(cmdline_options=[
            # CLS: I think this is a bug in their CMakeLists.txt, but you have to have Release enabled
            # in order to change the default of ASTERA_HARDEN_ENGINE (which defaults to ON? doesn't make sense for debug builds)
            '-DCMAKE_BUILD_TYPE=Release',
            '-DASTERA_HARDEN_ENGINE=OFF'
        ]),
        apt_deps=['mesa-common-dev', 'libx11-dev', 'libxrandr-dev', 'libxi-dev',
            'xorg-dev:all',     # use :all to prevent substituting :apt_arch
            'libgl1-mesa-dev', 'libglu1-mesa-dev', 'libopenal-dev']
    ),
]

# def create_game_list() -> List[str]:
#     return [cpr().name for cpr in game_list]

c_game_list = ProjectList('c_games', lambda: [cpr().name for cpr in c_game_recipes])

docker_tests = [
    # CreateProjectRecipe(build_system='cmake', git_remote='https://github.com/superjer/tinyc.games',
    #     source_languages=[LANG_C])

    # not really a game but oh well hahaha
    # CreateProjectRecipe(build_system='make', git_remote='https://github.com/orangeduck/Corange',
    #                     source_languages=[LANG_C])


]
