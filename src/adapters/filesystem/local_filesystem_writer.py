from pathlib import Path

from src.shared.exceptions.output_exceptions import ArtifactWriteError


class LocalFilesystemWriter:
    """Adapter implementing FilesystemWriter using pathlib.Path.

    This is the ONLY file in the codebase that imports pathlib and uses open().
    The core OutputManager depends on the FilesystemWriter Protocol only.
    """

    def create_directory(self, path: str) -> None:
        """Creates directory and all missing parents.

        Args:
            path: Target directory path.

        Raises:
            ArtifactWriteError: If directory creation fails.
        """
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            raise ArtifactWriteError(f"Failed to create directory '{path}': {exc}") from exc

    def directory_exists(self, path: str) -> bool:
        """Returns True if path is an existing directory."""
        return Path(path).is_dir()

    def write_text(self, path: str, content: str) -> None:
        """Writes UTF-8 text content to a file.

        Args:
            path: Full file path.
            content: Content to write.

        Raises:
            ArtifactWriteError: If write fails.
        """
        try:
            Path(path).write_text(content, encoding="utf-8")
        except Exception as exc:
            raise ArtifactWriteError(f"Failed to write file '{path}': {exc}") from exc

    def file_exists(self, path: str) -> bool:
        """Returns True if path is an existing regular file."""
        return Path(path).is_file()

    def join(self, base: str, *parts: str) -> str:
        """Joins path components using pathlib."""
        return str(Path(base).joinpath(*parts))
