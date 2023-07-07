import subprocess

from .. import BuildSystemDriver
from .. import RunConfig, ProjectBuild

class MakeDriver(BuildSystemDriver):
    def __init__(self) -> None:
        super().__init__('make')

    def _do_configure(self, runconfig: RunConfig, build: ProjectBuild):
        configure_opts = build.recipe.configure_options.cmdline_options

        # TODO: TEST THIS - IS MY PATH RIGHT HERE??
        # subprocess.run(['echo CALEB TEST: PATH=$PATH'], shell=True)
        subprocess.run([build.project_root/'configure', *configure_opts])

    def _do_build(self, runconfig: RunConfig, build: ProjectBuild, numjobs:int = 1):
        build_opts = build.recipe.build_options.cmdline_options
        p = subprocess.run(['make', f'-j{numjobs}', *build_opts])
        if p.returncode != 0:
            raise Exception(f'make build failed with return code {p.returncode}')

    def _do_clean(self, runconfig: RunConfig, build: ProjectBuild):
        clean_opts = build.recipe.clean_options.cmdline_options
        # alternatively, we could delete the build folder?
        subprocess.run(['make', 'clean', *clean_opts])
