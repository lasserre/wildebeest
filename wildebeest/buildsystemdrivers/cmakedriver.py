import subprocess

from .. import BuildSystemDriver
from .. import RunConfig, ProjectBuild

class CmakeDriver(BuildSystemDriver):
    def __init__(self) -> None:
        super().__init__('cmake')

    def _do_configure(self, runconfig: RunConfig, build: ProjectBuild):
        configure_opts = build.recipe.configure_options.cmdline_options

        # TODO: TEST THIS - IS MY PATH RIGHT HERE??
        subprocess.run(['echo CALEB TEST: PATH=$PATH'], shell=True)
        subprocess.run(['cmake', build.project_root, *configure_opts])

    def _do_build(self, runconfig: RunConfig, build: ProjectBuild, numjobs:int = 1):
        build_opts = build.recipe.build_options.cmdline_options
        subprocess.run(['echo CALEB TEST: PATH=$PATH'], shell=True)
        p = subprocess.run(['cmake', '--build', '.', f'-j{numjobs}', *build_opts])
        if p.returncode != 0:
            raise Exception(f'cmake build failed with return code {p.returncode}')

    def _do_clean(self, runconfig: RunConfig, build: ProjectBuild):
        clean_opts = build.recipe.clean_options.cmdline_options
        subprocess.run(['cmake', '--build', '.', '--target', 'clean', *clean_opts])
