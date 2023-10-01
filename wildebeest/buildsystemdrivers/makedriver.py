import subprocess
import shutil

from .. import BuildSystemDriver
from .. import RunConfig, ProjectBuild

class MakeDriver(BuildSystemDriver):
    def __init__(self) -> None:
        super().__init__('make')

    def _do_configure(self, runconfig: RunConfig, build: ProjectBuild):
        configure_opts = build.recipe.configure_options.cmdline_options

        # TODO: TEST THIS - IS MY PATH RIGHT HERE??
        # subprocess.run(['echo CALEB TEST: PATH=$PATH'], shell=True)
        configure = build.project_root/'configure' if build.recipe.supports_out_of_tree else './configure'
        subprocess.run([configure, *configure_opts])

    def _do_build(self, runconfig: RunConfig, build:ProjectBuild, numjobs:int = 1):
        build_opts = build.recipe.build_options.cmdline_options
        build_cmd = ['make', f'-j{numjobs}', *build_opts]
        self._do_subprocess_build(build, build_cmd)

    def _do_clean(self, runconfig: RunConfig, build: ProjectBuild):
        clean_opts = build.recipe.clean_options.cmdline_options
        # alternatively, we could delete the build folder?
        # subprocess.run(['make', 'clean', *clean_opts])
        shutil.rmtree(build.build_folder)
