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
]
