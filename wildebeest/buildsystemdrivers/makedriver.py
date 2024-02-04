import os
import subprocess
import shutil

from .. import BuildSystemDriver
from .. import RunConfig, ProjectBuild

class MakeDriver(BuildSystemDriver):
    def __init__(self) -> None:
        super().__init__('make')

    def _do_configure(self, runconfig: RunConfig, build: ProjectBuild, script_name:str='configure'):
        configure_opts = build.recipe.configure_options.cmdline_options

        configure = build.project_root/f'{script_name}' if build.recipe.supports_out_of_tree else f'./{script_name}'
        print(f'$CC="{os.environ["CC"]}"')
        print(f'Running: {" ".join([str(x) for x in [configure, *configure_opts]])}')

        subprocess.run(" ".join(str(x) for x in [configure, *configure_opts]), shell=True)

    def _do_build(self, runconfig: RunConfig, build:ProjectBuild, numjobs:int = 1):
        build_opts = build.recipe.build_options.cmdline_options
        build_cmd = ['make', f'-j{numjobs}', *build_opts]
        print(' '.join(build_cmd))
        print(f'BUILD: $CC="{os.environ["CC"]}"')
        print(f'BUILD: $CFLAGS="{os.environ["CFLAGS"]}"')
        self._do_subprocess_build(build, build_cmd)

    def _do_clean(self, runconfig: RunConfig, build: ProjectBuild):
        clean_opts = build.recipe.clean_options.cmdline_options
        # alternatively, we could delete the build folder?
        # subprocess.run(['make', 'clean', *clean_opts])
        shutil.rmtree(build.build_folder)
