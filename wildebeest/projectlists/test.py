from typing import List

from .. import ProjectList

# small project list for testing

def create_test_list() -> List[str]:
    return [
        'test-programs-cbasic'
    ]

test_list = ProjectList('test', create_test_list)
