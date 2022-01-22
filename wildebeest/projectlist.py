from typing import Callable, List

class ProjectList:
    def __init__(self, name, create_list:Callable[[],List[str]]) -> None:
        self.name = name
        self.create_list = create_list

    def __call__(self) -> List[str]:
        return self.create_list()
