from typing import List

from .. import *
from ..sourcelanguages import *

def create_c_projects() -> List[str]:
    return [r.name for r in get_recipes() if LANG_C in r.source_languages]

def create_c_only_projects() -> List[str]:
    return [r.name for r in get_recipes() if len(r.source_languages) == 1 and r.source_languages[0] == LANG_C]

c_projects = ProjectList('c_projects', create_c_projects)
c_only_projects = ProjectList('c_only_projects', create_c_only_projects)
