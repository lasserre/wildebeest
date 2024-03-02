import subprocess

from .. import BuildSystemDriver
from .. import RunConfig, ProjectBuild

class MesonDriver(BuildSystemDriver):
    def __init__(self) -> None:
        super().__init__('meson')

    def _do_configure(self, runconfig: RunConfig, build: ProjectBuild, **kwargs):
        config_opts = build.recipe.configure_options
        cmdline_opts = config_opts.cmdline_options

        # let runconfig generate the flags strings so that we do it the same way
        # as other build systems (which just read the env vars)
        configure_env = runconfig.generate_env(config_opts.extra_cflags, config_opts.extra_cxxflags, config_opts.linker_flags)
        cflags = configure_env['CFLAGS']
        cxxflags = configure_env['CXXFLAGS']

        # NOTE: rely on LDFLAGS env var for linker flags since I ran into issues trying
        # to supply -Dc_link_args="" ...I think it overwrote needed flags instead of appending
        # (untested since I'm not using linker flags right now, but I think it will work based on:
        # https://mesonbuild.com/howtox.html#set-extra-compiler-and-linker-flags-from-the-outside-when-eg-building-distro-packages)

        cmdline = f'meson setup --buildtype=plain -Dc_args="{cflags}" -Dcpp_args="{cxxflags}" '\
            f'{build.project_root} {" ".join(str(x) for x in cmdline_opts)}'

        print(f'MESON CONFIGURE CMD: {cmdline}', flush=True)
        subprocess.run(cmdline, shell=True)

    def _do_build(self, runconfig: RunConfig, build: ProjectBuild, numjobs:int = 1):
        build_opts = build.recipe.build_options.cmdline_options
        build_cmd = ['meson', 'compile', '-j', str(numjobs)]
        if build_opts:
            build_cmd.extend(str(x) for x in build_opts)
        print(f'MESON BUILD CMD: {" ".join(str(x) for x in build_cmd)}', flush=True)
        self._do_subprocess_build(build, build_cmd)

    def _do_clean(self, runconfig: RunConfig, build: ProjectBuild):
        raise Exception(f'_do_clean not implemented for meson')

