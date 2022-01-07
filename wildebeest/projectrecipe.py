
class ProjectRecipe:
    '''
    Represents the unique steps and information required to build a particular
    project
    '''
    def __init__(self, build_system:str, git_remote:str) -> None:
        '''
        build_system: The name of the build system (driver) that this project uses
        git_remote: A path or URL for the project's git repository from which it
                    may be cloned
        '''
        self.build_system = build_system
        self.git_remote = git_remote
