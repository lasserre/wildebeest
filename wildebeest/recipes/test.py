from typing import List

from ..sourcelanguages import *
from ..projectrecipe import ProjectRecipe

class CreateProjectRecipe:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def __call__(self) -> ProjectRecipe:
        return ProjectRecipe(**self.kwargs)

def cbasic_only():
    recipe = ProjectRecipe('cmake', 'git@github.com:lasserre/test-programs.git',
        name='test-programs (cbasic only)',
        source_languages=[LANG_CPP, LANG_C])
    recipe.build_options.cmdline_options = ['--target', 'cabasic']
    return recipe

recipe_list = [
    # List of Callables that -> ProjectRecipe
    CreateProjectRecipe(build_system='cmake', git_remote='git@github.com:lasserre/test-programs.git',
        source_languages=[LANG_CPP, LANG_C]),
    cbasic_only,
]