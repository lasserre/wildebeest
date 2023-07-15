from pathlib import Path
from typing import Any, Callable, List
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # avoid cyclic dependencies this way :)
    from .projectbuild import ProjectBuild

from .runconfig import RunConfig

class BuildStepOptions:
    def __init__(self,
            cmdline_options:List[str]=[],
            override_step:Callable[[RunConfig, 'ProjectBuild'], Any]=None,
            preprocess:Callable[[RunConfig, 'ProjectBuild'], Any]=None,
            postprocess:Callable[[RunConfig, 'ProjectBuild'], Any]=None) -> None:
        '''
        cmdline_options: Additional options for this build step that will be passed
                         on the command line as-is.
        override_step:  If supplied, this Callable will be called instead of the
                        build driver's default implementation. This should be used
                        as a last resort if customizing the other options isn't
                        sufficient.
        preprocess:     Optional callback to run just before this build step
        postprocess:    Optional callback to run immediately after this build step
        '''
        self.cmdline_options = cmdline_options
        '''Additional options that will be passed on the command line as-is'''
        self.override_step = override_step
        '''Overrides the build drivers default implementation for this step'''
        self.preprocess = preprocess
        '''Optional callback to run just before this step'''
        self.postprocess = postprocess
        '''Optional callback to run immediately after this step'''
        self.capture_stdout:Path = None
        '''
        Parameter to allow an algorithm to run a build step with the output
        written to a specific file
        '''

class ProjectRecipe:
    '''
    Represents the unique steps and information required to build a particular
    project.

    A project recipes is intended to be a reusable build script for a specific
    project that may be used for any experiment. Thus, care must be taken to not
    overconstrain the build options in the project recipe (e.g. specifying an
    optimization level or comiling with debug information). Only customize options
    that must be specified for the specific project in order for it to build
    successfully.
    '''
    def __init__(self, build_system:str, git_remote:str,
            name:str='',
            source_languages:List[str]=[],
            out_of_tree:bool=True,
            git_head:str='',
            apt_deps:List[str]=[],
            configure_options:BuildStepOptions=None,
            build_options:BuildStepOptions=None,
            clean_options:BuildStepOptions=None) -> None:
        '''
        name: A unique name for this recipe that can be used to identify it later
        build_system: The name of the build system (driver) that this project uses
        git_remote:  A path or URL for the project's git repository from which it
                     may be cloned
        source_languages:   Specifies the source code languages used by this project
                            (values should be the defined LANG_XX strings).
                            The first entry is assumed to be the primary language.
        out_of_tree: True if the project may be built "out-of-tree" in a separate build folder.
                     Most projects work this way, but occasionally, poorly-structured projects
                     scatter build artifacts throughout the source tree. In this case we have to
                     do separate clones for each build, so this option notifies us on a project
                     by project basis.
        git_head: If specified, this pathspec will be used to check out a specific
                  revision of the project instead of the default master/main/etc.
        apt_deps: List of apt packages which are build dependencies for this project
        configure_options: Custom configure options specific to this project
        build_options:  Custom build options specific to this project
        clean_options:  Custom clean options specific to this project
        '''
        self.name = name if name else Path(git_remote.split('/')[-1]).stem
        '''The unique name for this recipe'''
        self.build_system = build_system
        '''The name of the build system driver that this project uses'''
        self.git_remote = git_remote
        '''A path or URL for the project's git repository from which it may be cloned'''
        self.source_languages = source_languages
        '''The source code languages used by this project. First entry is the primary language'''
        self.supports_out_of_tree = out_of_tree
        '''
        True if the project may be built out-of-tree in a separate build folder.
        Most projects work this way
        '''
        self.git_head = git_head
        '''If specified, check out this revision of the project instead of the default'''
        self.apt_deps = apt_deps
        '''List of apt packages which are build dependencies for this project'''
        self.configure_options = configure_options if configure_options else BuildStepOptions()
        '''Custom configure options specific to this project'''
        self.build_options = build_options if build_options else BuildStepOptions()
        '''Custom build options specific to this project'''
        self.clean_options = clean_options if clean_options else BuildStepOptions()
        '''Custom clean options specific to this project'''

    @property
    def docker_image_name(self) -> str:
        return f'recipe_{self.name}'.lower()
