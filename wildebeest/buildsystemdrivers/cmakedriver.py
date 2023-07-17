import subprocess

from .. import BuildSystemDriver
from .. import RunConfig, ProjectBuild

class CmakeDriver(BuildSystemDriver):
    def __init__(self) -> None:
        super().__init__('cmake')

    def _do_configure(self, runconfig: RunConfig, build: ProjectBuild):
        configure_opts = build.recipe.configure_options.cmdline_options
        # I think the configure options (e.g. -Dxyz) have to come before the path
        subprocess.run(['cmake', *configure_opts, build.project_root])

        # if this ever becomes a problem again:
        # you can disable the initial compiler check (when you run "cmake ..") by
        # supplying -DCMAKE_C_COMPILER_WORKS=1 (or C++ version)
        # -> this bit me when using "-ast-dump=json -fsyntax-only" because no exe was built
        # e.g:
        # run.build.recipe.configure_options.cmdline_options.append('-DCMAKE_C_COMPILER_WORKS=1')

    def _do_build(self, runconfig: RunConfig, build: ProjectBuild, numjobs:int = 1):
        subprocess.run(['echo CALEB TEST: CFLAGS=$CFLAGS'], shell=True)

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
