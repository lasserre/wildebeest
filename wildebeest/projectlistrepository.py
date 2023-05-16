from importlib import metadata
from pathlib import Path
from typing import Callable, Dict, List

from wildebeest.projectrecipe import ProjectRecipe

from .projectlist import ProjectList
from .reciperepository import get_recipe

class ProjectListRepository:
    def __init__(self) -> None:
        self.project_lists = self._load_project_lists()

    def _load_project_lists(self) -> Dict[str, ProjectList]:
        '''
        Loads all project lists that may be found from the
        wildebeest.project_lists entry point
        '''
        pl_dict = {}
        pl_eps = []
        if 'wildebeest.project_lists' in metadata.entry_points():
            pl_eps = metadata.entry_points()['wildebeest.project_lists']
        for ep in pl_eps:
            pl:ProjectList = ep.load()
            pl_dict[pl.name] = pl
        return pl_dict

_pl_repo:ProjectListRepository = None

def _get_pl_repo() -> ProjectListRepository:
    global _pl_repo
    if _pl_repo is None:
        _pl_repo = ProjectListRepository()
    return _pl_repo

def get_project_list(name:str) -> List[ProjectRecipe]:
    '''
    Gets an instance of the ProjectList with the indicated name, or
    raises an exeption if it is not a registered recipe.
    '''
    repo = _get_pl_repo()
    if name in repo.project_lists:
        recipe_names = repo.project_lists[name]()   # call the ProjectList instance
        return [get_recipe(r) for r in recipe_names]
    raise Exception(f'Experiment {name} not a registered project list')

def get_project_list_names() -> List[str]:
    '''Returns a list of registered project list names'''
    repo = _get_pl_repo()
    return list(repo.project_lists.keys())

