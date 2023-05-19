from ..projectrecipe import ProjectRecipe

class CreateProjectRecipe:
    '''
    Putting an explanation here because I came back to this later and was like
    "why on earth did make CreateProjectRecipe instead of just calling ProjectRecipe()?"

    Because project recipe lists have to be CALLABLES (not instances) this is just
    the Callable wrapper around ProjectRecipe!
    '''
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def __call__(self) -> ProjectRecipe:
        return ProjectRecipe(**self.kwargs)
