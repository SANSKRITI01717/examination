"""
Pydantic schemas for Answer listing and Workspace detail (N1, N2).
Contract: api-spec.md §9 and architecture.md §8.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ocr import AnswerOCRResponse


class AnswerRowResponse(BaseModel):
    id: int
    anon_code: str
    question_number: str
    marking_status: str
    ocr_status: str
    ai_status: str
    ocr_review_required: bool
    final_marks: Optional[float] = None
    max_marks: float

    model_config = ConfigDict(from_attributes=True)


class AnswerListResponse(BaseModel):
    items: List[AnswerRowResponse]
    total: int
    page: int
    page_size: int


class AnswerQuestionInfo(BaseModel):
    id: int
    question_number: str
    text: str
    max_marks: float
    evaluation_mode: str

    model_config = ConfigDict(from_attributes=True)


class AnswerPageInfo(BaseModel):
    id: int
    page_number: int
    image_url: str

    model_config = ConfigDict(from_attributes=True)


class AnswerNavigationInfo(BaseModel):
    position: int
    total: int
    prev_answer_id: Optional[int] = None
    next_answer_id: Optional[int] = None


class ExaminerInfo(BaseModel):
    id: int
    full_name: str


class EvaluationSummary(BaseModel):
    id: int
    marks_awarded: float
    criterion_marks: Optional[List[Dict[str, Any]]] = None
    comment: Optional[str] = None
    source: str
    status: str
    submitted_at: Optional[str] = None
    examiner: ExaminerInfo

    model_config = ConfigDict(from_attributes=True)


class AnswerDetailResponse(BaseModel):
    id: int
    exam_id: int
    anon_code: str
    question: AnswerQuestionInfo
    rubric: Optional[Dict[str, Any]] = None
    pages: List[AnswerPageInfo]
    is_attempted: bool
    ocr: AnswerOCRResponse
    ai: Dict[str, Any]
    evaluation: Optional[EvaluationSummary] = None
    marking_status: str
    final_marks: Optional[float] = None
    final_source: Optional[str] = None
    anomalies: Optional[List[Dict[str, Any]]] = None
    moderation: Optional[Dict[str, Any]] = None
    navigation: AnswerNavigationInfo
    student: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
