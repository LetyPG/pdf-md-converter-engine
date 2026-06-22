from typing import Protocol


class FilesystemWriter(Protocol):
    """Protocol defining the filesystem operations used by OutputManager.

    The core OutputManager depends exclusively on this Protocol.
    No pathlib, os, or open() call ever appears in the core domain.

    Implementors:
        - LocalFilesystemWriter (src/adapters/filesystem/local_filesystem_writer.py)
    """

    def create_directory(self, path: str) -> None:
        """Creates a directory (and any missing parents).

        Args:
            path: Absolute or relative path to the directory to create.

        Raises:
            OutputError: If the directory cannot be created.
        """
        ...

    def directory_exists(self, path: str) -> bool:
        """Returns True if the path exists and is a directory."""
        ...

    def write_text(self, path: str, content: str) -> None:
        """Writes a UTF-8 text string to the given file path.

        Args:
            path: Full path to the target file (file and parent dir must exist).
            content: String content to write.

        Raises:
            ArtifactWriteError: If the write fails.
        """
        ...

    def file_exists(self, path: str) -> bool:
        """Returns True if the path exists and is a regular file."""
        ...

    def join(self, base: str, *parts: str) -> str:
        """Joins path components in a platform-safe manner.

        Equivalent to str(Path(base) / part1 / part2 / ...).
        """
        ...
