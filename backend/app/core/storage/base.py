"""
Abstract storage service interface per backend-plan.md §3.
"""
from abc import ABC, abstractmethod


class StorageService(ABC):
    @abstractmethod
    def save(self, storage_key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        """Save bytes to storage at the given key and return the key."""
        pass

    @abstractmethod
    def get(self, storage_key: str) -> bytes:
        """Retrieve bytes from storage by key. Raises FileNotFoundError if missing."""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Check if file exists at the given key."""
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Delete file at the given key."""
        pass
