"""
OCR package exports and factory.
"""
from app.ai.ocr.base import OCRProvider, OCRResult
from app.ai.ocr.confidence import evaluate_ocr_confidence
from app.ai.ocr.preprocess import preprocess_image
from app.ai.ocr.vision_provider import VisionOCRProvider

_ocr_instance: OCRProvider = None


def get_ocr_provider() -> OCRProvider:
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = VisionOCRProvider()
    return _ocr_instance


__all__ = [
    "OCRProvider",
    "OCRResult",
    "get_ocr_provider",
    "preprocess_image",
    "evaluate_ocr_confidence",
]
