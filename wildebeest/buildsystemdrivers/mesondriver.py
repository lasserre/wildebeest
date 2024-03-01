import subprocess

from .. import BuildSystemDriver
from .. import RunConfig, ProjectBuild

class MesonDriver(BuildSystemDriver):
    def __init__(self) -> None:
        super().__init__('meson')

    def _do_configure(self, runconfig: RunConfig, build: ProjectBuild, **kwargs):
        opts = build.recipe.configure_options.cmdline_options

        # let runconfig generate the flags strings so that we do it the same way
        # as other build systems (which just read the env vars)
        configure_env = runconfig.generate_env(opts.extra_cflags, opts.extra_cxxflags, opts.linker_flags)
        cflags = configure_env['CFLAGS']
        cxxflags = configure_env['CXXFLAGS']
        ldflags = configure_env['LDFLAGS'] if 'LDFLAGS' in configure_env else ''

        cmdline = f'meson setup --buildtype=plain -Dc_args="{cflags}" -Dcpp_args="{cxxflags}" -Dc_link_args="{ldflags}" -Dcpp_link_args="{ldflags}" '\
            f'{build.project_root} {" ".join(str(x) for x in opts)}'

        print(f'meson commandline: {cmdline}')
        subprocess.run(cmdline, shell=True)

    def _do_build(self, runconfig: RunConfig, build: ProjectBuild, numjobs:int = 1):
        build_opts = build.recipe.build_options.cmdline_options
        build_cmd = f'meson compile -j {numjobs} {" ".join(str(x) for x in build_opts)}'
        self._do_subprocess_build(build, build_cmd)

    def _do_clean(self, runconfig: RunConfig, build: ProjectBuild):
        raise Exception(f'_do_clean not implemented for meson')

