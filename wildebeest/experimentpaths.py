from pathlib import Path

class ExpRelPaths:
    '''Experiment folder relative paths'''
    Wdb = Path('.wildebeest')
    ExpYaml = Wdb/'exp.yaml'
    Runstates = Wdb/'runstates'
    Source = Path('source')
    Build = Path('build')
    Rundata = Path('rundata')
    Expdata = Path('expdata')