
class ProjectRecipe:
    '''
    Represents the unique steps and information required to build a particular
    project
    '''
    def __init__(self, build_system:str, git_remote:str, out_of_tree:bool=True) -> None:
        '''
        build_system: The name of the build system (driver) that this project uses
        git_remote:  A path or URL for the project's git repository from which it
                     may be cloned
        out_of_tree: True if the project may be built "out-of-tree" in a separate build folder.
                     Most projects work this way, but occasionally, poorly-structured projects
                     scatter build artifacts throughout the source tree. In this case we have to
                     do separate clones for each build, so this option notifies us on a project
                     by project basis.
        '''
        self.build_system = build_system
        '''The name of the build system driver that this project uses'''

        self.git_remote = git_remote
        '''A path or URL for the project's git repository from which it may be cloned'''

        self.supports_out_of_tree = out_of_tree
        '''
        True if the project may be built out-of-tree in a separate build folder.
        Most projects work this way
        '''
