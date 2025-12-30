
class BuildException(Exception):
    def __init__(self, message: str, *args):
        self.message = message
        super().__init__(args)


class FileTypeError(OSError):
    """This file type is not supported."""

    def __init__(self, message: str, file_type: str) -> None:
        self.message = message
        self.type = file_type
        super().__init__(message)
