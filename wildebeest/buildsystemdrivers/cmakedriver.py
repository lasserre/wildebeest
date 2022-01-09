import subprocess

from .. import BuildSystemDriver
from .. import RunConfig, ProjectBuild

class CmakeDriver(BuildSystemDriver):
    def __init__(self) -> None:
        super().__init__('cmake')

    def _do_configure(self, runconfig: RunConfig, build: ProjectBuild):
        subprocess.run(['cmake', build.project_root])

    def _do_build(self, runconfig: RunConfig, build: ProjectBuild, numjobs: int = 1):
        subprocess.run(['cmake', '--build', '.', f'-j{numjobs}'])

    def _do_clean(self, runconfig: RunConfig, build: ProjectBuild):
        subprocess.run(['cmake', '--build', '.', '--target', 'clean'])
