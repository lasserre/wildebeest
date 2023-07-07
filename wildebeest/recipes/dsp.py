from wildebeest.sourcelanguages import LANG_C, LANG_CPP
from . import CreateProjectRecipe
from .. import ProjectList
from typing import List

dsp_recipes = [
    CreateProjectRecipe(build_system='make', git_remote='https://github.com/FFmpeg/FFmpeg.git',
        source_languages=[LANG_C]),
]

dsp_list = ProjectList('dsp', lambda: [cpr().name for cpr in dsp_recipes])
