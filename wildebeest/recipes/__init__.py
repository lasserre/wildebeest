from ..projectrecipe import ProjectRecipe

class CreateProjectRecipe:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def __call__(self) -> ProjectRecipe:
        return ProjectRecipe(**self.kwargs)
