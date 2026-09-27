"""
Pydantic schemas for Anomalies (AN1-AN3).
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class AnomalyDetectRequest(BaseModel):
    detectors: Optional[List[str]] = None


class AnomalyDetectResponse(BaseModel):
    created: int
    updated: int
    by_type: Dict[str, int]


class AnomalyPatchRequest(BaseModel):
    status: str
    note: Optional[str] = None


class AnomalyResponse(BaseModel):
    id: int
    exam_id: int
    type: str
    severity: str
    answer_id: Optional[int]
    question_id: Optional[int]
    examiner_id: Optional[int]
    score: Optional[float]
    details: Dict[str, Any]
    status: str
    note: Optional[str]
    detected_at: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class AnomalyListResponse(BaseModel):
    items: List[AnomalyResponse]
    total: int
    page: int
    page_size: int
