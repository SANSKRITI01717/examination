"""
Pydantic schemas for AnswerSheet, AnswerSheetPage, Mapping, and Assignments (AS1-AS6).
Contract: api-spec.md §7 and database-schema.md §6, §7.
"""
from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.student import StudentResponse

SheetStatusType = Literal["uploaded", "mapped"]
AssignmentStrategyType = Literal["by_sheet", "by_question"]


class AnswerSheetPageResponse(BaseModel):
    id: int
    sheet_id: int
    page_number: int
    image_url: str
    width: Optional[int] = None
    height: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class AnswerSummary(BaseModel):
    id: int
    question_id: int
    question_number: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    is_attempted: bool
    ocr_status: str
    ai_status: str
    marking_status: str
    final_marks: Optional[float] = None
    max_marks: float

    model_config = ConfigDict(from_attributes=True)


class AnswerSheetResponse(BaseModel):
    id: int
    exam_id: int
    student_id: Optional[int] = None
    anon_code: str
    status: SheetStatusType
    page_count: int
    created_at: datetime
    student: Optional[StudentResponse] = None
    mapped: Optional[bool] = None
    answers_total: Optional[int] = None
    answers_marked: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class AnswerSheetListResponse(BaseModel):
    items: List[AnswerSheetResponse]
    total: int
    page: int
    page_size: int


class AnswerSheetDetailResponse(AnswerSheetResponse):
    pages: List[AnswerSheetPageResponse] = []
    answers: List[AnswerSummary] = []


class MappingItem(BaseModel):
    question_id: int
    page_start: int = Field(..., ge=1)
    page_end: int = Field(..., ge=1)
    is_attempted: bool = True


class MappingRequest(BaseModel):
    items: List[MappingItem]


class AssignmentRequest(BaseModel):
    examiner_ids: List[int] = Field(..., min_length=1)
    strategy: AssignmentStrategyType = "by_sheet"


class AssignmentResponse(BaseModel):
    assigned: int
    per_examiner: Dict[str, int]
