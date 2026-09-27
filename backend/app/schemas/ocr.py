"""
Pydantic schemas for OCR operations (O1-O4).
Contract: api-spec.md §8 and architecture.md §8.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BatchOCRRequest(BaseModel):
    answer_ids: Optional[List[int]] = Field(
        None, description="Optional subset of answer IDs to process. If omitted, all pending/failed attempted answers in the exam are queued."
    )


class BatchOCRResponse(BaseModel):
    queued: int = Field(..., description="Number of answers queued for OCR processing")


class AnswerTextUpdateRequest(BaseModel):
    verified_text: Optional[str] = Field(
        None, description="Corrected transcript of the student's handwritten answer"
    )
    ocr_verified: bool = Field(
        True, description="Flag indicating human examiner has verified the text"
    )


class AnswerOCRResponse(BaseModel):
    status: str
    text: Optional[str] = None
    verified_text: Optional[str] = None
    confidence: Optional[float] = None
    review_required: bool = False
    verified: bool = False

    model_config = ConfigDict(from_attributes=True)


class ProcessingCounters(BaseModel):
    pending: int = 0
    processing: int = 0
    done: int = 0
    failed: int = 0


class AIMarkingCounters(BaseModel):
    not_requested: int = 0
    pending: int = 0
    processing: int = 0
    done: int = 0
    failed: int = 0


class MarkingCounters(BaseModel):
    pending: int = 0
    marked: int = 0
    flagged: int = 0
    moderated: int = 0


class ProcessingStatusResponse(BaseModel):
    ocr: ProcessingCounters
    ai: AIMarkingCounters
    review_required: int
    marking: MarkingCounters
