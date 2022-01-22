from importlib import metadata
from pathlib import Path
from typing import Dict

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
        exp_eps = metadata.entry_points()['wildebeest.experiments']
        for ep in exp_eps:
            exp_class = ep.load()
            exp_dict[exp_class().name] = exp_class
        return exp_dict

_experiment_repo = None

def create_experiment(name:str, **kwargs) -> Experiment:
    '''
    Creates an instance of the Experiment with the indicated name, or
    raises an exeption if it is not a registered experiment.
    '''
    global _experiment_repo
    if not _experiment_repo:
        _experiment_repo = ExperimentRepository()

    if name in _experiment_repo.experiments:
        exp:Experiment = _experiment_repo.experiments[name](**kwargs)  # construct a new instance
        if exp.exp_folder.exists():
            raise Exception(f'Experiment folder {exp.exp_folder} already exists')
        return exp
    raise Exception(f'Experiment {name} not a registered experiment')

def load_experiment(exp_folder:Path) -> Experiment:
    '''
    Loads the given experiment from it's experiment yaml file

    Helper function for API parity with create_experiment :)
    '''
    return Experiment.load_from_yaml(exp_folder)
