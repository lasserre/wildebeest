from importlib import metadata
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

def get_experiment(name:str, **kwargs) -> Experiment:
    '''
    Creates (or loads) an instance of the Experiment with the indicated name, or
    None if it is not a registered experiment.

    If the experiment folder is given (via parent_folder in kwargs) and the experiment
    folder already exists, it will be loaded and returned instead of a fresh experiment
    instance.
    '''
    global _experiment_repo
    if not _experiment_repo:
        _experiment_repo = ExperimentRepository()

    if name in _experiment_repo.experiments:
        exp:Experiment = _experiment_repo.experiments[name](**kwargs)  # construct a new instance
        if exp.exp_folder.exists():
            exp = Experiment.load_from_yaml(exp.exp_folder)
            if exp.name != name:
                print(f'Warning: experiment folder {exp.exp_folder} already exists, but name is different')
                print(f'Existing name = {exp.name}, requested name = {name}')
        return exp
    return None
