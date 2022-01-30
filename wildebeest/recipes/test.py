from typing import List

from ..sourcelanguages import *
from ..projectrecipe import ProjectRecipe

from . import CreateProjectRecipe

def cbasic_only():
    recipe = ProjectRecipe('cmake', 'git@github.com:lasserre/test-programs.git',
        name='test-programs-cbasic',
        source_languages=[LANG_CPP, LANG_C])
    recipe.build_options.cmdline_options = ['--target', 'cbasic']
    return recipe

recipe_list = [
    # List of Callables that -> ProjectRecipe
    CreateProjectRecipe(build_system='cmake', git_remote='git@github.com:lasserre/test-programs.git',
        source_languages=[LANG_CPP, LANG_C]),
    cbasic_only,
]
