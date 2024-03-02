from wildebeest.sourcelanguages import LANG_C, LANG_CPP
from . import CreateProjectRecipe
from .. import ProjectList
from ..projectrecipe import BuildStepOptions
from typing import List

misc_c_recipes = [
    # CLS: don't want to include C++ right now
    CreateProjectRecipe(
        build_system='meson',
        git_remote='https://github.com/rizinorg/rizin',
        git_head='v0.7.0',
        name='rizin',
        source_languages=[LANG_C],
    ),

    CreateProjectRecipe(git_remote='https://github.com/warmcat/libwebsockets.git',
        build_system='cmake',
        git_head='v4.3.3',
        name='libwebsockets',
        source_languages=[LANG_C],
        apt_deps = ['libssl-dev'],
    ),

    CreateProjectRecipe(git_remote='https://github.com/neutrinolabs/xrdp/releases/download/v0.9.24/xrdp-0.9.24.tar.gz',
        build_system='make',
        name='xrdp',
        source_languages=[LANG_C],
        apt_deps = ['libssl-dev', 'libpam-dev', 'libx11-dev', 'libxfixes-dev', 'libxrandr-dev', 'pkg-config', 'nasm'],
        # Redhat deps: openssl-devel, pam-devel, libX11-devel, libXfixes-devel, libXrandr-devel
        no_cc_wrapper=False,    # try the wrapper...
    ),

    CreateProjectRecipe(git_remote='https://github.com/slembcke/Chipmunk2D/archive/refs/tags/Chipmunk-7.0.3.tar.gz',
        build_system='cmake',
        name='chipmunk',
        source_languages=[LANG_C],
        apt_deps = ['freeglut3-dev', 'libxmu-dev', 'libxrandr-dev', 'libx11-dev'],
        no_cc_wrapper=False,    # try the wrapper
    ),
]
