from typing import Any, Dict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # avoid cyclic dependencies this way
    from ..experiment import Experiment

from ..experimentalgorithm import ExpStep

def _clone_repos(exp:'Experiment', params:Dict[str,Any], outputs:Dict[str,Any]):
    '''
    I'm seeing some races with parallel builds sharing the same source folder, so
    I can (always? optionally?) add this preprocessing step to ensure each project's
    source code is cloned FIRST before kicking off build jobs
        > specifically, jobs are racing by checking if source folder EXISTS, but
        > maybe the code isn't fully cloned yet!

    If I know I don't need this for an experiment (one build per repository) I
    COULD omit it...however I think we will usually be rerunning postprocessing
    on a set of pre-built stuff, so might be a good default
    '''
    for run in exp.load_runs():
        # this doesn't have races because we're not running in parallel right now
        run.build.init_project_root()

def clone_repos() -> ExpStep:
    '''
    Returns an ExpStep to clone all project repos before kicking off jobs, to avoid
    races between multiple builds sharing the same project code
    (I observed such races very early on)
    '''
    return ExpStep('clone_repos', _clone_repos, {})
