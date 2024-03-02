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
        ldflags = configure_env['LDFLAGS'] if 'LDFLAGS' in configure_env else ''

        cmdline = f'meson setup --buildtype=plain -Dc_args="{cflags}" -Dcpp_args="{cxxflags}" -Dc_link_args="{ldflags}" -Dcpp_link_args="{ldflags}" '\
            f'{build.project_root} {" ".join(str(x) for x in cmdline_opts)}'

        print(f'MESON CONFIGURE CMD: {cmdline}', flush=True)
        subprocess.run(cmdline, shell=True)

    def _do_build(self, runconfig: RunConfig, build: ProjectBuild, numjobs:int = 1):
        build_opts = build.recipe.build_options.cmdline_options
        build_cmd = ['meson', 'compile', '-j', str(numjobs), " ".join(str(x) for x in build_opts)]
        print(f'MESON BUILD CMD: {" ".join(str(x) for x in build_cmd)}', flush=True)
        self._do_subprocess_build(build, build_cmd)

    def _do_clean(self, runconfig: RunConfig, build: ProjectBuild):
        raise Exception(f'_do_clean not implemented for meson')

