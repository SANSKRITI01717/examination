"""
Storage package factory per backend-plan.md §3.
"""
from app.core.config import settings
from app.core.storage.base import StorageService
from app.core.storage.local import LocalStorage

_storage_instance: StorageService = None


def get_storage() -> StorageService:
    global _storage_instance
    if _storage_instance is None:
        if settings.STORAGE_BACKEND == "local":
            _storage_instance = LocalStorage()
        else:
            # Fallback to local for now or when s3 is not configured
            _storage_instance = LocalStorage()
    return _storage_instance


__all__ = ["StorageService", "LocalStorage", "get_storage"]
