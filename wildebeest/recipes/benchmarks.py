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
    apt_deps = ['texinfo', 'build-essential', 'flex', 'bison', 'libgmp-dev'],
    configure_options=BuildStepOptions(cmdline_options=['--disable-nls']),
    no_cc_wrapper=True,
)

bc_v1_07 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/bc/bc-1.07.tar.gz',
    name='bc_v1.07',
    build_system='make',
    source_languages=[LANG_C],
    out_of_tree=False,
    apt_deps = ['ed'],
)

bash_v5_2 = CreateProjectRecipe(git_remote='https://github.com/bminor/bash.git',
    name='bash_v5.2',
    git_head = 'bash-5.2',
    build_system='make',
    source_languages=[LANG_C],
    out_of_tree=False,
    no_cc_wrapper=True,
)

bison_v3_7 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/bison/bison-3.7.tar.gz',
    name='bison_v3.7',
    build_system='make',
    source_languages=[LANG_C],
    out_of_tree=False,
    apt_deps = [],
    no_cc_wrapper=True,
)

def do_make_defconfig(runconfig: RunConfig, build: ProjectBuild):
    import subprocess
    print(f'Running make defconfig...')
    if runconfig.opt_level == '-O0':
        config_file = build.build_folder/'.config'
        print(f'Fixing config file {config_file}')
        subprocess.run(f"sed -e 's/.*CONFIG_DEBUG\s.*/CONFIG_DEBUG=y/' -i {config_file}", shell=True)
        subprocess.run(f"sed -e 's/.*DEBUG_PESSIMIZE.*/CONFIG_DEBUG_PESSIMIZE=y/' -i {config_file}", shell=True)
    p = subprocess.run(['make', 'defconfig'])
    if p.returncode != 0:
        raise Exception(f'{runconfig.name} make defconfig failed with return code {p.returncode}')

busybox_v1_33_1 = CreateProjectRecipe(git_remote='https://github.com/mirror/busybox.git',
    name='busybox_v1_33_1',
    git_head='1_33_1',
    build_system='make',
    source_languages=[LANG_C],
    out_of_tree=False,
    # no_cc_wrapper=True,
    apt_deps = [],
    configure_options=BuildStepOptions(override_step=do_make_defconfig),
)

benchmark_recipes = [
    coreutils_v8_32,
    binutils_v2_36,
    bash_v5_2,
    bc_v1_07,
    bison_v3_7,
    busybox_v1_33_1,
]

coreutils_list = ProjectList('coreutils', lambda: [coreutils_v8_32().name])

# Jan 2021 is my date for approximating "latest versions" used in StateFormer benchmarks
stateformer33 = ProjectList('stateformer33', lambda: [
    bash_v5_2().name,
    binutils_v2_36().name,
])
