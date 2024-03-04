from wildebeest.sourcelanguages import LANG_C, LANG_CPP
from . import CreateProjectRecipe
from .. import ProjectList
from ..projectrecipe import BuildStepOptions
from typing import List
import subprocess

def run_autoreconf(rc, build, **kwargs):
    p = subprocess.run('autoreconf -fiv', shell=True)
    if p.returncode != 0:
        raise Exception(f'autoreconf failed with return code {p.returncode}')

def run_bootstrap(rc, build, **kwargs):
    p = subprocess.run('./bootstrap', shell=True)
    if p.returncode != 0:
        raise Exception(f'./bootstrap failed with return code {p.returncode}')

misc_c_recipes = [
    # CLS: don't want to include C++ right now
    CreateProjectRecipe(
        build_system='meson',
        git_remote='https://github.com/rizinorg/rizin',
        git_head='v0.7.0',
        name='rizin',
        source_languages=[LANG_C],
    ),

    CreateProjectRecipe(git_remote='https://github.com/warmcat/libwebsockets.git',
        build_system='cmake',
        git_head='v4.3.3',
        name='libwebsockets',
        source_languages=[LANG_C],
        apt_deps = ['libssl-dev'],
    ),

    CreateProjectRecipe(git_remote='https://github.com/neutrinolabs/xrdp/releases/download/v0.9.24/xrdp-0.9.24.tar.gz',
        build_system='make',
        name='xrdp',
        source_languages=[LANG_C],
        apt_deps = ['libssl-dev', 'libpam-dev', 'libx11-dev', 'libxfixes-dev', 'libxrandr-dev', 'pkg-config', 'nasm'],
        # Redhat deps: openssl-devel, pam-devel, libX11-devel, libXfixes-devel, libXrandr-devel
        no_cc_wrapper=False,    # try the wrapper...
    ),

    CreateProjectRecipe(git_remote='https://github.com/slembcke/Chipmunk2D/archive/refs/tags/Chipmunk-7.0.3.tar.gz',
        build_system='cmake',
        name='chipmunk',
        source_languages=[LANG_C],
        apt_deps = ['freeglut3-dev', 'libxmu-dev', 'libxrandr-dev', 'libx11-dev'],
        no_cc_wrapper=False,    # try the wrapper
    ),

    CreateProjectRecipe(git_remote='https://github.com/glfw/glfw/archive/refs/tags/3.4.tar.gz',
        build_system='cmake',
        name='glfw',
        source_languages=[LANG_C],
        apt_deps=['libwayland-dev', 'libxkbcommon-dev', 'xorg-dev:all'],
    ),

    CreateProjectRecipe(git_remote='https://github.com/allinurl/goaccess/archive/refs/tags/v1.9.1.tar.gz',
        build_system='make',
        name='goaccess',
        out_of_tree=False,
        source_languages=[LANG_C],
        configure_options=BuildStepOptions(cmdline_options=['--enable-utf8', '--enable-geoip=mmdb'], preprocess=run_autoreconf),
        apt_deps=['autopoint', 'gettext', 'libmaxminddb-dev'],
        no_cc_wrapper=False,    # try the wrapper
    ),

    CreateProjectRecipe(git_remote='https://github.com/jedisct1/libsodium/releases/download/1.0.19-RELEASE/libsodium-1.0.19.tar.gz',
        build_system='make',
        name='libsodium',
        source_languages=[LANG_C],
    ),

    CreateProjectRecipe(git_remote='https://github.com/videolan/vlc.git',
        git_head='3.0.18',
        build_system='make',
        name='vlc',
        source_languages=[LANG_C],
        apt_deps=['libtool', 'automake', 'autopoint', 'gettext', 'pkg-config', 'flex', 'bison', 'lua5.2', 'liblua5.2-dev', 'libavcodec-dev',
                'libavformat-dev', 'libswscale-dev', 'liba52-0.7.4-dev', 'xcb', 'libxcb1-dev', 'libxcb-shm0-dev', 'libxcb-composite0-dev',
                'libxcb-xv0-dev', 'libxcb-randr0-dev', 'libasound2-dev'],
        # git g++ make libtool automake autopoint pkg-config flex bison lua5.2
        configure_options=BuildStepOptions(preprocess=run_bootstrap),
        out_of_tree=False,
        no_cc_wrapper=False,    # try the wrapper
    ),

    CreateProjectRecipe(git_remote='https://github.com/python/cpython.git',
        name='cpython',
        git_head='v3.12.2',
        build_system='make',
        source_languages=[LANG_C],
        # from https://devguide.python.org/getting-started/setup-building/#build-dependencies
        apt_deps=['build-essential', 'gdb', 'lcov', 'pkg-config', 'libbz2-dev', 'libffi-dev', 'libgdbm-dev', 'libgdbm-compat-dev', 'liblzma-dev',
                'libncurses5-dev', 'libreadline6-dev', 'libsqlite3-dev', 'libssl-dev', 'lzma', 'lzma-dev', 'tk-dev', 'uuid-dev', 'zlib1g-dev'],
        no_cc_wrapper=False,    # try the wrapper
    ),

    CreateProjectRecipe(git_remote='https://github.com/kraj/musl.git',
        name='musl',
        git_head='v1.2.5',
        build_system='make',
        source_languages=[LANG_C],
    ),

    CreateProjectRecipe(git_remote='https://github.com/wine-mirror/wine.git',
        name='wine',
        git_head='wine-9.3',
        build_system='make',
        source_languages=[LANG_C],
        configure_options=BuildStepOptions(cmdline_options=['--enable-win64']),
        # from https://wiki.winehq.org/Building_Wine
        apt_deps=['gcc-mingw-w64', 'libasound2-dev', 'libpulse-dev', 'libdbus-1-dev', 'libfontconfig-dev', 'libfreetype-dev', 'libgnutls28-dev',
                'libgl-dev', 'libunwind-dev', 'libx11-dev', 'libxcomposite-dev', 'libxcursor-dev', 'libxfixes-dev', 'libxi-dev', 'libxrandr-dev',
                'libxrender-dev', 'libxext-dev', 'libgstreamer1.0-dev', 'libgstreamer-plugins-base1.0-dev', 'libosmesa6-dev', 'libsdl2-dev', 'libudev-dev',
                'libvulkan-dev', 'libcapi20-dev', 'libcups2-dev', 'libgphoto2-dev', 'libsane-dev', 'libkrb5-dev', 'samba-dev', 'ocl-icd-opencl-dev', 'libpcap-dev',
                'libusb-1.0-0-dev', 'libv4l-dev',
                'flex', 'bison']
    ),

    CreateProjectRecipe(git_remote='https://github.com/redis/redis/archive/refs/tags/7.2.4.tar.gz',
        name='redis',
        build_system='make',
        source_languages=[LANG_C],
        out_of_tree=False,
        no_cc_wrapper=False,    # try the wrapper
        config_script_name='../../../../../../usr/bin/make',
            # FIXME: hack to try this without remaking the base exp image since things are running
            # (need to add a skip_configure option really...)
    ),
]
