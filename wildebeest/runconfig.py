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

class DebugFlags:
    WITH_DEBUG = ['-g']
    '''Flags to compile with debug information'''

class CompilationSettings:
    '''
    Customize compilation settings for a build. Any options left to the
    default value will not be constrained when invoking the build system
    (e.g. default compiler_path means build system will use a default compiler).
    '''
    compiler_path: Path
    compiler_flags: List[str]
    linker_flags: List[str]

    def __init__(self) -> None:
        self.compiler_path = None
        '''Path to desired compiler executable'''
        self.compiler_flags = []
        '''List of additional compiler arguments'''
        self.append_compiler_flags = False
        '''If set, compiler flags will be appended to any existing flags set
        in environment variables (e.g. CFLAGS) rather than replacing them'''
        self.linker_flags = []
        '''List of additional linker arguments'''

    def add_c_cpp_vars(self, env_dict:dict, lang:str):
        '''
        Adds CC/CFLAGS or CXX/CXXFLAGS variables to the environment dictionary from the

        env_dict: The dictionary to add the environment variables to
        lang: Either LANG_C or LANG_CPP to specify desired language
        '''
        compilervar = 'CC' if lang == LANG_C else 'CXX'
        flagsvar = 'CFLAGS' if lang == LANG_C else 'CXXFLAGS'

        if self.compiler_path:
            env_dict[compilervar] = str(self.compiler_path)
        if self.compiler_flags:
            existing = []
            if flagsvar in os.environ and self.append_compiler_flags:
                existing = os.environ[flagsvar].split()
            env_dict[flagsvar] = ' '.join([*existing, *self.compiler_flags])

class RunConfig:
    '''
    Settings that describe the configuration for a single run of an experiment
    '''
    compile_options: Dict[str, CompilationSettings]

    def __init__(self) -> None:
        self.compile_options = {}
        '''
        Dictionary mapping language name to its compilation options. The C and C++
        language options are guaranteed to exist, but other languages may add
        to this dictionary if needed.
        '''
        self.compile_options[LANG_C] = CompilationSettings()
        self.compile_options[LANG_CPP] = CompilationSettings()

    @property
    def c_options(self) -> CompilationSettings:
        return self.compile_options[LANG_C]

    @property
    def cpp_options(self) -> CompilationSettings:
        return self.compile_options[LANG_CPP]

    def generate_env(self) -> Dict[str,str]:
        '''
        Generates a dictionary of environment variable key/value pairs
        representing the RunConfig
        '''
        env_dict = {}
        self.c_options.add_c_cpp_vars(env_dict, LANG_C)
        self.cpp_options.add_c_cpp_vars(env_dict, LANG_CPP)
        return env_dict
