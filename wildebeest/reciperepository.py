from importlib import metadata
from pathlib import Path
from typing import Callable, Dict, List

from .projectrecipe import ProjectRecipe

class RecipeRepository:
    def __init__(self) -> None:
        self.recipes = self._load_recipes()

    def _load_recipes(self) -> Dict[str, Callable[[],ProjectRecipe]]:
        '''
        Loads all ProjectRecipes that may be found from the
        wildebeest.recipes entry point
        '''
        recipe_dict = {}
        recipe_eps = []
        if 'wildebeest.recipes' in metadata.entry_points():
            recipe_eps = metadata.entry_points()['wildebeest.recipes']
        for ep in recipe_eps:
            recipe_list:List[Callable[[],ProjectRecipe]] = ep.load()
            for create_recipe in recipe_list:
                r = create_recipe()
                if r.name not in recipe_dict:
                    recipe_dict[r.name] = create_recipe
        return recipe_dict

_recipe_repo:RecipeRepository = None

def _get_recipe_repo() -> RecipeRepository:
    global _recipe_repo
    if _recipe_repo is None:
        _recipe_repo = RecipeRepository()
    return _recipe_repo

def get_recipe(name:str) -> ProjectRecipe:
    '''
    Gets an instance of the ProjectRecipe with the indicated name, or
    raises an exeption if it is not a registered recipe.
    '''
    repo = _get_recipe_repo()
    if name in repo.recipes:
        return repo.recipes[name]()   # construct a new instance
    raise Exception(f'Experiment {name} not a registered recipe name')

def get_recipe_names() -> List[str]:
    '''Returns a list of registered recipe names'''
    repo = _get_recipe_repo()
    return list(repo.recipes.keys())

def get_recipes() -> List[ProjectRecipe]:
    '''
    Return a list of all registered project recipes
    '''
    return [get_recipe(r) for r in get_recipe_names()]
