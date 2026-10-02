"""File storage behind a tiny interface.

Today files go to a local folder. When the project moves to Azure (as the
report plans), only this module changes: a BlobStorage class with the same
three methods. Nothing else in the codebase touches the filesystem directly.
"""
import os
import uuid
from pathlib import Path

from app.core.config import get_settings


class LocalFileStorage:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)

    def save(self, folder: str, extension: str, content: bytes) -> str:
        """Write bytes under base_dir/<folder>/<random>.<ext>; return the relative key."""
        directory = self.base_dir / folder
        directory.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex}.{extension.lstrip('.')}"
        (directory / name).write_bytes(content)
        return f"{folder}/{name}"

    def absolute_path(self, key: str) -> Path:
        return self.base_dir / key

    def delete(self, key: str) -> None:
        path = self.absolute_path(key)
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


_storage: LocalFileStorage | None = None


def get_storage() -> LocalFileStorage:
    global _storage
    if _storage is None:
        _storage = LocalFileStorage(get_settings().upload_dir)
    return _storage
