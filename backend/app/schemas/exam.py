"""
Pydantic schemas for Exam models.
Mirrors api-spec.md §4 and frontend/src/api/types.ts.
"""
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


ExamStatusType = Literal["draft", "evaluation", "moderation", "completed"]


class ExamSettings(BaseModel):
    ocr_low_conf_threshold: Optional[float] = Field(0.80, ge=0.0, le=1.0)
    ai_low_conf_threshold: Optional[float] = Field(0.70, ge=0.0, le=1.0)
    ai_disagreement_ratio: Optional[float] = Field(0.30, ge=0.0, le=1.0)
    too_fast_seconds: Optional[int] = Field(10, ge=1)
    z_threshold: Optional[float] = Field(2.5, gt=0.0)
    min_sample_size: Optional[int] = Field(10, ge=1)
    retrieval_top_k: Optional[int] = Field(4, ge=1)
    retrieval_min_score: Optional[float] = Field(0.50, ge=0.0, le=1.0)

    model_config = ConfigDict(extra="allow")


class ExamCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    course_code: str = Field(..., min_length=1, max_length=50)
    exam_date: Optional[date] = None
    settings: Optional[Dict[str, Any]] = None


class ExamUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    course_code: Optional[str] = Field(None, min_length=1, max_length=50)
    exam_date: Optional[date] = None
    settings: Optional[Dict[str, Any]] = None


class ExamTransitionRequest(BaseModel):
    to: Literal["evaluation", "moderation", "completed"]


class ExamResponse(BaseModel):
    id: int
    title: str
    course_code: str
    exam_date: Optional[date] = None
    status: ExamStatusType
    settings: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExamDetailResponse(ExamResponse):
    question_count: int = 0
    sheet_count: int = 0
    answer_count: int = 0
