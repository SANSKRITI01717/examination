"""
Pydantic schemas for Question and Rubric models.
Mirrors api-spec.md §5 and frontend/src/api/types.ts.
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


EvaluationModeType = Literal["standard", "reference_grounded"]


class RubricCriterion(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    max_marks: float = Field(..., gt=0)
    description: Optional[str] = None


class RubricCreate(BaseModel):
    criteria: List[RubricCriterion] = Field(..., min_length=1)
    guidance: Optional[str] = None


class RubricResponse(BaseModel):
    question_id: int
    criteria: List[RubricCriterion]
    guidance: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class QuestionCreate(BaseModel):
    question_number: str = Field(..., min_length=1, max_length=10)
    text: str = Field(..., min_length=1)
    max_marks: float = Field(..., gt=0)
    evaluation_mode: Optional[EvaluationModeType] = "standard"
    display_order: Optional[int] = 0


class QuestionUpdate(BaseModel):
    question_number: Optional[str] = Field(None, min_length=1, max_length=10)
    text: Optional[str] = Field(None, min_length=1)
    max_marks: Optional[float] = Field(None, gt=0)
    evaluation_mode: Optional[EvaluationModeType] = None
    display_order: Optional[int] = None


class QuestionResponse(BaseModel):
    id: int
    exam_id: int
    question_number: str
    text: str
    max_marks: float
    evaluation_mode: EvaluationModeType
    display_order: int
    rubric: Optional[RubricResponse] = None

    model_config = ConfigDict(from_attributes=True)
