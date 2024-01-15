from wildebeest.sourcelanguages import LANG_C, LANG_CPP
from . import CreateProjectRecipe
from .. import ProjectList
from ..projectrecipe import BuildStepOptions
from typing import List

from .. import RunConfig, ProjectBuild

dsp_recipes = [
    CreateProjectRecipe(build_system='make',
        git_remote='https://github.com/FFmpeg/FFmpeg.git',
        source_languages=[LANG_C],
        apt_deps=['nasm'],
        configure_options=BuildStepOptions(
                # CLS: first attempt at dynamically-generated configure options!
                # OPTION 2: rc.c_options.compiler_path
                preprocess=lambda rc, pb: print('IN CONFIGURE PREPROCESS') or pb.recipe.configure_options.cmdline_options.append(f'--cc=$CC')
            )
        ),
]

dsp_list = ProjectList('dsp', lambda: [cpr().name for cpr in dsp_recipes])
