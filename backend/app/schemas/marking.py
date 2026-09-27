"""
Pydantic schemas for examiner marking (M1, M2).
Contract: api-spec.md §12. criterion_marks shape follows database-schema.md
(evaluations.criterion_marks = [{"criterion_id", "awarded_marks"}]).
"""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class AcceptAIRequest(BaseModel):
    ai_evaluation_id: int
    active_seconds: int = Field(..., ge=0)


class CriterionMarkInput(BaseModel):
    criterion_id: str
    awarded_marks: float


class SaveMarksRequest(BaseModel):
    marks_awarded: float
    criterion_marks: Optional[List[CriterionMarkInput]] = None
    comment: Optional[str] = None
    # ai_accepted is only reachable through M1 (accept-ai), never through M2.
    source: Literal["ai_modified", "manual"]
    ai_evaluation_id: Optional[int] = None
    active_seconds: int = Field(..., ge=0)
    submit: bool


class EvaluationExaminer(BaseModel):
    id: int
    full_name: str


class EvaluationResponse(BaseModel):
    id: int
    marks_awarded: float
    criterion_marks: Optional[List[Dict[str, Any]]] = None
    comment: Optional[str] = None
    source: str
    status: str
    submitted_at: Optional[str] = None
    examiner: EvaluationExaminer

    model_config = ConfigDict(from_attributes=True)
