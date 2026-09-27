"""
Local filesystem storage implementation per backend-plan.md §3.
"""
from pathlib import Path
from app.core.config import settings
from app.core.storage.base import StorageService


class LocalStorage(StorageService):
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or settings.LOCAL_STORAGE_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, storage_key: str) -> Path:
        clean_key = storage_key.lstrip("/").replace("\\", "/")
        full_path = (self.base_dir / clean_key).resolve()
        # Ensure path traversal prevention
        if not str(full_path).startswith(str(self.base_dir)):
            raise ValueError("Path traversal attempt detected")
        return full_path

    def save(self, storage_key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        file_path = self._resolve_path(storage_key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        return storage_key

    def get(self, storage_key: str) -> bytes:
        file_path = self._resolve_path(storage_key)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"Storage file not found: {storage_key}")
        return file_path.read_bytes()

    def exists(self, storage_key: str) -> bool:
        file_path = self._resolve_path(storage_key)
        return file_path.exists() and file_path.is_file()

    def delete(self, storage_key: str) -> None:
        file_path = self._resolve_path(storage_key)
        if file_path.exists():
            file_path.unlink()
