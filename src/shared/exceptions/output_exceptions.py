class OutputError(Exception):
    """Base exception for all Output Manager failures."""


class ArtifactWriteError(OutputError):
    """Raised when a file cannot be written or verified after writing."""


class SerializationError(OutputError):
    """Raised when a data contract cannot be serialized to JSON."""


class CollisionError(OutputError):
    """Raised when all collision-resolution suffixes (_001–_999) are exhausted."""
