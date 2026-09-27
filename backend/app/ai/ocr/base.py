"""
OCR Provider interface and result data structures per backend-plan.md §3.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class OCRResult:
    text: str
    confidence: float
    meta: Dict[str, Any] = field(default_factory=dict)


class OCRProvider(ABC):
    @abstractmethod
    def extract_text(self, image_bytes: bytes) -> OCRResult:
        """Extract text and confidence score from image bytes."""
        pass
