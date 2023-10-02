import os
from pathlib import Path
from typing import List, Dict

from .sourcelanguages import *

class ClangFlags:
    def load_plugin(plugin_path:Path, plugin_name:str) -> List[str]:
        '''
        Generates the (verbose) list of flags to pass to clang to load the
        specified clang plugin

        plugin_path: Path to the plugin .so
        plugin_name: Registered name of the plugin as recognized by clang
        '''
        # FORMAT: -Xclang -load -Xclang <my_plugin.so> -Xclang -add-plugin -Xclang <my_plugin>
        return ' -Xclang '.join(['', '-load', str(plugin_path), '-add-plugin', plugin_name]).split()

class LinuxCompilerFlags:
    '''
    These should apply to gcc/clang at least
    '''
    # FYI: https://stackoverflow.com/questions/48754619/what-are-cmake-build-type-debug-release-relwithdebinfo-and-minsizerel

    ENABLE_DEBUG = ['-g']
    '''Flags to compile with debug information'''

class CompilationSettings:
    '''
    Customize compilation settings for a build. Any options left to the
    default value will not be constrained when invoking the build system
    (e.g. default compiler_path means build system will use a default compiler).
    '''
    compiler_path: Path
    compiler_flags: List[str]

    def __init__(self, append_flags:bool=False) -> None:
        self.compiler_path = None
        '''Path to desired compiler executable'''
        self.compiler_flags = []
        '''List of additional compiler arguments'''
        self.append_compiler_flags = append_flags
        '''If set, compiler flags will be appended to any existing flags set
        in environment variables (e.g. CFLAGS) rather than replacing them'''

    def enable_debug_info(self):
        '''
        Ensures the flags defined for compiling with debug info are included
        (LinuxCompilerFlags.ENABLE_DEBUG)

        Not all gcc/clang flags work this way, but for the debug info flags I'm
        using now, we can add/remove them freely by inspecting the whole list.
        Other flags don't work that way (e.g. -Xclang), so this approach doesn't work in general
        '''
        for f in LinuxCompilerFlags.ENABLE_DEBUG:
            if f not in self.compiler_flags:
                self.compiler_flags.append(f)

    def disable_debug_info(self):
        '''
        Ensures the flags defined for compiling with debug info are not included
        '''
        for f in LinuxCompilerFlags.ENABLE_DEBUG:
            if f in self.compiler_flags:
                self.compiler_flags.remove(f)

    def add_c_cpp_vars_to_env(self, env_dict:dict, recipe_compiler_flags:List[str], lang:str):
        '''
        Adds CC/CFLAGS or CXX/CXXFLAGS variables to the environment dictionary from
        this instance's relevant settings

        env_dict: The dictionary to add the environment variables to
        lang: Either LANG_C or LANG_CPP to specify desired language
        '''
        compilervar = 'CC' if lang == LANG_C else 'CXX'
        flagsvar = 'CFLAGS' if lang == LANG_C else 'CXXFLAGS'

        if self.compiler_path:
            env_dict[compilervar] = str(self.compiler_path)
        if self.compiler_flags or recipe_compiler_flags:
            existing = []
            if flagsvar in os.environ and self.append_compiler_flags:
                existing = os.environ[flagsvar].split()
            env_dict[flagsvar] = ' '.join([*existing, *self.compiler_flags, *recipe_compiler_flags])

class RunConfig:
    '''
    Settings that describe the configuration for a single run of an experiment
    '''
    compile_options: Dict[str, CompilationSettings]
    num_build_jobs: int
    linker_flags: List[str]

    def __init__(self, name:str='default') -> None:
        '''
        name: An optional human-readable name for the run
        '''
        self.name = name
        self.compile_options = {}
        '''
        Dictionary mapping language name to its compilation options. The C and C++
        language options are guaranteed to exist, but other languages may add
        to this dictionary if needed.
        '''
        self.compile_options[LANG_C] = CompilationSettings()
        self.compile_options[LANG_CPP] = CompilationSettings()

        # linker flags (LDFLAGS) apply to both C and C++ using this mechanism
        # if we need C/C++-specific linker settings, use compiler flags to pass
        # linker flags through (e.g. -Wl)
        self.linker_flags = []
        '''List of additional linker arguments'''
        self.append_linker_flags = False
        '''If set, linker flags will be appended to any existing flags set
        in environment variables (LDFLAGS) rather than replacing them'''

        self.num_build_jobs = 1
        '''Default number of build jobs to use per build (e.g. make -j N)'''

    @property
    def c_options(self) -> CompilationSettings:
        return self.compile_options[LANG_C]

    @property
    def cpp_options(self) -> CompilationSettings:
        return self.compile_options[LANG_CPP]

    def generate_env(self, recipe_cflags:List[str],
                     recipe_cxxflags:List[str], recipe_linker_flags:List[str]) -> Dict[str,str]:
        '''
        Generates a dictionary of environment variable key/value pairs
        representing the RunConfig
        '''
        env_dict = {}
        self.c_options.add_c_cpp_vars_to_env(env_dict, recipe_cflags, LANG_C)
        self.cpp_options.add_c_cpp_vars_to_env(env_dict, recipe_cxxflags, LANG_CPP)

        # add linker flags to LDFLAGS only 1x (not within add_c_cpp_vars multiple times)
        if self.linker_flags or recipe_linker_flags:
            existing = []
            if 'LDFLAGS' in os.environ and self.append_linker_flags:
                existing = os.environ['LDFLAGS'].split()
            env_dict['LDFLAGS'] = ' '.join([*existing, *self.linker_flags, *recipe_linker_flags])

        return env_dict
