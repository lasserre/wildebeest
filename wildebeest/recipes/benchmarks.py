from wildebeest.sourcelanguages import LANG_C, LANG_CPP
from . import CreateProjectRecipe

from ..projectrecipe import BuildStepOptions
from .. import RunConfig, ProjectBuild, ProjectList

def pre_config_coreutils(rc:RunConfig, build:ProjectBuild):
    import subprocess
    p = subprocess.run(['./bootstrap'], shell=True)
    if p.returncode != 0:
        raise Exception(f'./bootstrap script failed with code {p.returncode}')

coreutils_v8_32 = CreateProjectRecipe(build_system='make', git_remote='https://github.com/coreutils/coreutils.git',
                    name='coreutils_v8.32',
                    git_head='v8.32',
                    source_languages=[LANG_C],
                    out_of_tree=False,
                    configure_options=BuildStepOptions(preprocess=pre_config_coreutils),
                    apt_deps=['autoconf', 'automake', 'bison', 'gettext', 'git', 'gperf', 'gzip',
                              'perl', 'rsync', 'texinfo']
                    )

benchmark_recipes = [
    coreutils_v8_32,
]

coreutils_list = ProjectList('coreutils', lambda: [coreutils_v8_32().name])
