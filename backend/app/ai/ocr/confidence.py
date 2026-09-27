"""
OCR confidence computation and verification requirement rules per ai-pipeline.md §2.
"""
from typing import Any, Dict, List


def evaluate_ocr_confidence(
    text: str,
    confidence: float,
    word_confidences: List[float],
    settings: Dict[str, Any],
    is_attempted: bool = True,
) -> bool:
    """
    Determine if human verification is required (answers.ocr_review_required).
    Rule from ai-pipeline.md §2:
    review_required = true if ANY holds:
    1. ocr_confidence < ocr_low_conf_threshold (default 0.80)
    2. low_word_fraction (> 25% of words have confidence < 0.60)
    3. text is empty, or shorter than 20 characters while is_attempted = true
    """
    threshold = float(settings.get("ocr_low_conf_threshold", 0.80))

    # Condition 1: Overall confidence below threshold
    if confidence < threshold:
        return True

    # Condition 2: High proportion of low-confidence words
    if word_confidences:
        low_words = [w for w in word_confidences if w < 0.60]
        low_word_fraction = len(low_words) / float(len(word_confidences))
        if low_word_fraction > 0.25:
            return True

    # Condition 3: Empty or suspiciously short text for attempted answer
    clean_text = (text or "").strip()
    if is_attempted and len(clean_text) < 20:
        return True

    return False
