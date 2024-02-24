import subprocess

from .. import BuildSystemDriver
from .. import RunConfig, ProjectBuild

class CmakeDriver(BuildSystemDriver):
    def __init__(self) -> None:
        super().__init__('cmake')

    def _do_configure(self, runconfig: RunConfig, build: ProjectBuild, **kwargs):
        configure_opts = build.recipe.configure_options.cmdline_options

        cmdline = ["cmake", build.project_root, *configure_opts]

        print(f'cmake commandline: {" ".join(str(x) for x in cmdline)}')
        subprocess.run(cmdline)

    def _do_build(self, runconfig: RunConfig, build: ProjectBuild, numjobs:int = 1):
        build_opts = build.recipe.build_options.cmdline_options
        build_cmd = ['cmake', '--build', '.', f'-j{numjobs}', *build_opts]
        if build.recipe.build_options.capture_stdout:
            # want this effect to capture compiler stdout:
            #   cmake --build . -- VERBOSE=1
            build_cmd.extend(['--', 'VERBOSE=1'])
        self._do_subprocess_build(build, build_cmd)

    def _do_clean(self, runconfig: RunConfig, build: ProjectBuild):
        clean_opts = build.recipe.clean_options.cmdline_options
        subprocess.run(['cmake', '--build', '.', '--target', 'clean', *clean_opts])
