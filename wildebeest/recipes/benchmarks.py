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

imagemagick_v7_0_11_0 = CreateProjectRecipe(git_remote='https://github.com/ImageMagick/ImageMagick/archive/refs/tags/7.0.11-0.tar.gz',
    name='imagemagick-v7.0.11-0',
    build_system='make',
    source_languages=[LANG_C],
    configure_options=BuildStepOptions(cmdline_options=['--without-magick-plus-plus', 'CC=$CC', 'CFLAGS="$CFLAGS"', 'LDFLAGS="$LDFLAGS"']),
    no_cc_wrapper=True,
    out_of_tree=False,
)

indent_v2_2_12 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/indent/indent-2.2.12.tar.xz',
    name='indent-2.2.12',
    build_system='make',
    source_languages=[LANG_C],
    # their configure system is broken - configure should have defined HAVE_LOCALE_H
    configure_options=BuildStepOptions(cmdline_options=['CFLAGS="$CFLAGS -DHAVE_LOCALE_H"']),
    no_cc_wrapper=True,
    out_of_tree=False,
    apt_deps = ['build-essential', 'gperf', 'gettext'],
)

inetutils_v2_0 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/inetutils/inetutils-2.0.tar.gz',
    name='inetutils_v2.0',
    build_system='make',
    source_languages=[LANG_C],
)

less_v563 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/less/less-563.tar.gz',
    name='less-563',
    build_system='make',
    source_languages=[LANG_C],
)

gmp_v6_2_1 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/gmp/gmp-6.2.1.tar.xz',
    name='gmp-6.2.1',
    build_system='make',
    source_languages=[LANG_C],
)

libmicrohttpd_v0_9_72 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/libmicrohttpd/libmicrohttpd-0.9.72.tar.gz',
    name='libmicrohttpd-0.9.72',
    build_system='make',
    source_languages=[LANG_C],
)

libpng_v1_6_37 = CreateProjectRecipe(git_remote='https://github.com/pnggroup/libpng/archive/refs/tags/v1.6.37.tar.gz',
    name='libpng-1.6.37',
    build_system='make',
    source_languages=[LANG_C],
)

def do_nothing(rc, build, **kwargs):
    pass

libtomcrypt_v1_18_2 = CreateProjectRecipe(git_remote='https://github.com/libtom/libtomcrypt/archive/refs/tags/v1.18.2.tar.gz',
    name='libtomcrypt-1.18.2',
    build_system='make',
    source_languages=[LANG_C],
    # looks like no configure step, just "make"
    configure_options=BuildStepOptions(override_step=do_nothing),
    build_options=BuildStepOptions(cmdline_options=['-f', 'makefile.shared']),  # build shared library instead of just static one
    out_of_tree=False,
    apt_deps = ['libtool-bin'],
)

nano_v5_5 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/nano/nano-5.5.tar.xz',
    name='nano-5.5',
    build_system='make',
    source_languages=[LANG_C],
)

openssl_1_1_1k = CreateProjectRecipe(git_remote='https://github.com/openssl/openssl.git',
    name='openssl_1_1_1k',
    git_head='OpenSSL_1_1_1k',
    build_system='make',
    source_languages=[LANG_C],
    config_script_name='config',
    apt_deps = [],
)

def cd_to_unix(rc, build):
    import os
    os.chdir('unix')

# putty_v0_74 = CreateProjectRecipe(git_remote='https://github.com/github/putty/archive/refs/tags/0.74.tar.gz',
putty_v0_74 = CreateProjectRecipe(git_remote='https://the.earth.li/~sgtatham/putty/0.74/putty-0.74.tar.gz',
    name='putty-0.74',
    build_system='make',
    source_languages=[LANG_C],
    configure_options=BuildStepOptions(preprocess=cd_to_unix),
    build_options=BuildStepOptions(preprocess=cd_to_unix),
    clean_options=BuildStepOptions(preprocess=cd_to_unix),
    no_cc_wrapper=True,
    out_of_tree=False,
)

sed_v4_8 = CreateProjectRecipe(git_remote='https://mirrors.ibiblio.org/gnu/sed/sed-4.8.tar.xz',
    name='sed-4.8',
    build_system='make',
    source_languages=[LANG_C],
)

sg3_utils_v1_45 = CreateProjectRecipe(git_remote='https://github.com/hreinecke/sg3_utils/archive/refs/tags/v1.45.tar.gz',
    name='sg3-utils-1.45',
    build_system='make',
    source_languages=[LANG_C],
)

sqlite_v3_34_1 = CreateProjectRecipe(git_remote='https://github.com/sqlite/sqlite/archive/refs/tags/version-3.34.1.tar.gz',
    name='sqlite-3.34.1',
    build_system='make',
    source_languages=[LANG_C],
    apt_deps = ['tcl'],
)

def pre_config_usbutils(rc:RunConfig, build:ProjectBuild, **kwargs):
    import subprocess
    rc = subprocess.run('autoreconf --install --symlink', shell=True).returncode
    if rc != 0:
        raise Exception(f'autoreconf failed with return code {rc}')

usbutils_v013 = CreateProjectRecipe(git_remote='https://github.com/gregkh/usbutils/archive/refs/tags/v013.tar.gz',
    name='usbutils-v013',
    build_system='make',
    source_languages=[LANG_C],
    apt_deps = ['libusb-dev'],
    configure_options=BuildStepOptions(preprocess=pre_config_usbutils),
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
    indent_v2_2_12,
    inetutils_v2_0,
    less_v563,
    gmp_v6_2_1,
    libmicrohttpd_v0_9_72,
    libpng_v1_6_37,
    libtomcrypt_v1_18_2,
    nano_v5_5,
    openssl_1_1_1k,
    putty_v0_74,
    sed_v4_8,
    sg3_utils_v1_45,
    sqlite_v3_34_1,
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
    indent_v2_2_12().name,
    inetutils_v2_0().name,
    less_v563().name,
    gmp_v6_2_1().name,
    libmicrohttpd_v0_9_72().name,
    libpng_v1_6_37().name,
    libtomcrypt_v1_18_2().name,
    nano_v5_5().name,
    openssl_1_1_1k().name,
    putty_v0_74().name,
    sed_v4_8().name,
    sg3_utils_v1_45().name,
    sqlite_v3_34_1().name,
])
