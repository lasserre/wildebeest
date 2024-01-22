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
                    configure_options=BuildStepOptions(preprocess=pre_config_coreutils, extra_cflags=['-Wno-error']),
                    build_options=BuildStepOptions(extra_cflags=['-Wno-error']),
                    apt_deps=['autoconf', 'automake', 'autopoint', 'bison', 'gettext', 'git', 'gperf', 'gzip',
                              'perl', 'rsync', 'texinfo', 'wget']
                    )

binutils_v2_36 = CreateProjectRecipe(git_remote='git://sourceware.org/git/binutils-gdb.git',
    name='binutils-2_36',
    build_system='make',
    git_head='binutils-2_36',
    source_languages=[LANG_C],
    out_of_tree=True,   # not sure...
    apt_deps = ['texinfo', 'build-essential'],
    # if build-essential doesn't work, --disable-nls seems to be a popular option...
)

benchmark_recipes = [
    coreutils_v8_32,
    binutils_v2_36,
]

coreutils_list = ProjectList('coreutils', lambda: [coreutils_v8_32().name])

stateformer33 = ProjectList('stateformer33', lambda: [binutils_v2_36().name])
