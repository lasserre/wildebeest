from .. import BuildSystemDriver

class CmakeDriver(BuildSystemDriver):
    def __init__(self) -> None:
        super().__init__('cmake')

