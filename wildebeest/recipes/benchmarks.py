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

def do_make_defconfig(runconfig: RunConfig, build: ProjectBuild, **kwargs):
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

cflow_v1_6 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/cflow/cflow-1.6.tar.gz',
    name='cflow-v1.6',
    build_system='make',
    source_languages=[LANG_C],
    out_of_tree=False,
)

curl_v7_75_0 = CreateProjectRecipe(git_remote='https://github.com/curl/curl/releases/download/curl-7_75_0/curl-7.75.0.tar.gz',
    name='curl-v7.75.0',
    build_system='make',
    apt_deps = ['libssl-dev'],
    source_languages=[LANG_C],
    # --enable-debug --with-ssl CFLAGS='-g -O0'
    configure_options=BuildStepOptions(cmdline_options=['--enable-debug', '--with-ssl',
            'CC=$CC', 'CFLAGS="$CFLAGS"', 'LDFLAGS="$LDFLAGS"']),
    no_cc_wrapper=True,
    out_of_tree=False,
)

diffutils_v3_7 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/diffutils/diffutils-3.7.tar.xz',
    name='diffutils-v3.7',
    build_system='make',
    source_languages=[LANG_C],
)

dpkg_v1_20_6 = CreateProjectRecipe(git_remote='https://snapshot.debian.org/archive/debian-debug/20210108T082358Z/pool/main/d/dpkg/dpkg_1.20.6.tar.xz',
    name='dpkg_v1.20.6',
    build_system='make',
    source_languages=[LANG_C],
    apt_deps = ['perl', 'pkg-config'],
)

findutils_v4_8_0 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/findutils/findutils-4.8.0.tar.xz',
    name='findutils-v4.8.0',
    build_system='make',
    source_languages=[LANG_C],
)

gawk_v5_1_0 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/gawk/gawk-5.1.0.tar.xz',
    name='gawk-v5.1.0',
    build_system='make',
    source_languages=[LANG_C],
)

grep_v3_6 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/grep/grep-3.6.tar.xz',
    name='grep-v3.6',
    build_system='make',
    source_languages=[LANG_C],
)

gtypist_v2_9 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/gtypist/gtypist-2.9.tar.xz',
    name='gtypist-2.9',
    build_system='make',
    source_languages=[LANG_C],
    apt_deps = ['help2man'],
)

gzip_v1_10 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/gzip/gzip-1.10.tar.xz',
    name='gzip-v1.10',
    build_system='make',
    source_languages=[LANG_C],
)

# todo: more here...

imagemagick_v7_0_11_0 = CreateProjectRecipe(git_remote='https://github.com/ImageMagick/ImageMagick/archive/refs/tags/7.0.11-0.tar.gz',
    name='imagemagick-v7.0.11-0',
    build_system='make',
    source_languages=[LANG_C],
    configure_options=BuildStepOptions(cmdline_options=['--without-magick-plus-plus', 'CC=$CC', 'CFLAGS="$CFLAGS"', 'LDFLAGS="$LDFLAGS"']),
    no_cc_wrapper=True,
    out_of_tree=False,
)

openssl_1_1_1k = CreateProjectRecipe(git_remote='https://github.com/openssl/openssl.git',
    name='openssl_1_1_1k',
    git_head='OpenSSL_1_1_1k',
    build_system='make',
    source_languages=[LANG_C],
    config_script_name='config',
    apt_deps = [],
)

benchmark_recipes = [
    binutils_v2_36,
    bash_v5_2,
    bc_v1_07,
    bison_v3_7,
    busybox_v1_33_1,
    cflow_v1_6,
    coreutils_v8_32,
    curl_v7_75_0,
    diffutils_v3_7,
    dpkg_v1_20_6,
    findutils_v4_8_0,
    gawk_v5_1_0,
    grep_v3_6,
    gtypist_v2_9,
    gzip_v1_10,

    imagemagick_v7_0_11_0,
    openssl_1_1_1k,
]

coreutils_list = ProjectList('coreutils', lambda: [coreutils_v8_32().name])

# Jan 2021 is my date for approximating "latest versions" used in StateFormer benchmarks
stateformer33 = ProjectList('stateformer33', lambda: [
    bash_v5_2().name,
    bc_v1_07().name,
    binutils_v2_36().name,
    bison_v3_7().name,
    busybox_v1_33_1().name,
    cflow_v1_6().name,
    coreutils_v8_32().name,
    curl_v7_75_0().name,
    diffutils_v3_7().name,
    dpkg_v1_20_6().name,
    findutils_v4_8_0().name,
    gawk_v5_1_0().name,
    grep_v3_6().name,
    gtypist_v2_9().name,
    gzip_v1_10().name,

    imagemagick_v7_0_11_0().name,
])
