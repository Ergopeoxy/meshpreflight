"""The exception shared by all file readers."""


class MeshFormatError(ValueError):
    """The file could not be understood. The message explains why, in plain language."""
