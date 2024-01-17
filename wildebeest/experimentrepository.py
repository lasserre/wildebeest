from importlib import metadata
from pathlib import Path
from typing import Dict, List

from .experiment import Experiment

class ExperimentRepository:
    def __init__(self) -> None:
        self.experiments = self._load_experiments()

    def _load_experiments(self) -> Dict[str, Experiment]:
        '''
        Loads all Experiments that may be found from the
        wildebeest.experiments entry point
        '''
        exp_dict = {}
        EXPS_KEY = 'wildebeest.experiments'
        exp_eps = metadata.entry_points()[EXPS_KEY] if EXPS_KEY in metadata.entry_points() else []
        for ep in exp_eps:
            exp_class = ep.load()
            exp_dict[exp_class().name] = exp_class
        return exp_dict

_experiment_repo:ExperimentRepository = None

def _get_exp_repo() -> ExperimentRepository:
    global _experiment_repo
    if _experiment_repo is None:
        _experiment_repo = ExperimentRepository()
    return _experiment_repo

def create_experiment(name:str, **kwargs) -> Experiment:
    '''
    Creates an instance of the Experiment with the indicated name, or
    raises an exeption if it is not a registered experiment.
    '''
    repo = _get_exp_repo()
    if name in repo.experiments:
        exp:Experiment = repo.experiments[name](**kwargs)  # construct a new instance
        if exp.exp_folder.exists():
            raise Exception(f'Experiment folder {exp.exp_folder} already exists')
        return exp
    raise Exception(f'Experiment {name} not a registered experiment')

def load_experiment(exp_folder:Path) -> Experiment:
    '''
    Loads the given experiment from it's experiment yaml file

    Helper function for API parity with create_experiment :)
    '''
    return Experiment.load_exp_from_yaml(exp_folder)

def get_experiment_names() -> List[str]:
    repo = _get_exp_repo()
    return list(repo.experiments.keys())
