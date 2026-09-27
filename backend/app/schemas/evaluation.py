"""
Pydantic schemas for AI evaluation (V1, V3).
Contract: api-spec.md §10.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RunAIEvaluationRequest(BaseModel):
    force_standard: bool = Field(
        False,
        description="Skip reference retrieval for a reference_grounded question. "
        "Logged as mode_requested='standard'.",
    )


class CriterionResult(BaseModel):
    criterion_id: str
    criterion: str
    max_marks: float
    awarded_marks: float
    reason: str


class AIEvaluationResponse(BaseModel):
    id: int
    answer_id: int
    mode_requested: str
    mode_used: str
    model_name: str
    prompt_version: str
    suggested_marks: float
    max_marks: float
    confidence: float
    llm_confidence: Optional[float] = None
    criteria: List[CriterionResult]
    overall_reason: Optional[str] = None
    retrieval: Optional[List[Dict[str, Any]]] = None
    warnings: List[str] = []
    stale: bool = False
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AIEvaluationListResponse(BaseModel):
    items: List[AIEvaluationResponse]

class BatchRunAIEvaluationRequest(BaseModel):
    answer_ids: Optional[List[int]] = Field(default_factory=list)
    only_pending: bool = True

class BatchRunAIEvaluationResponse(BaseModel):
    queued: int
