import os
from pathlib import Path

def get_file_size_mb(file_path: str) -> float:
    """Returns the size of the file in megabytes."""
    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)

def get_file_extension(file_path: str) -> str:
    """Returns the lowercase file extension without the dot."""
    return Path(file_path).suffix.lower().lstrip('.')

def file_exists(file_path: str) -> bool:
    """Returns True if the file exists."""
    return os.path.exists(file_path)
