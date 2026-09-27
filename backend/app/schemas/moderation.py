from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, ConfigDict, Field

ModerationDecision = Literal["confirmed", "overridden"]
AnomalyType = str
AnomalySeverity = Literal["low", "medium", "high"]

class ModerationCreate(BaseModel):
    decision: ModerationDecision
    moderated_marks: float
    reason: Optional[str] = None

class ModerationResponse(BaseModel):
    id: int
    answer_id: int
    evaluation_id: Optional[int]
    moderator_id: int
    original_marks: Optional[float]
    moderated_marks: float
    decision: ModerationDecision
    reason: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class QueueAnomalySummary(BaseModel):
    type: AnomalyType
    severity: AnomalySeverity

class QueueExaminerSummary(BaseModel):
    id: int
    full_name: str

class ModerationQueueItem(BaseModel):
    answer_id: int
    anon_code: str
    question_number: str
    examiner: Optional[QueueExaminerSummary]
    marks: Optional[float]
    ai_suggested_marks: Optional[float]
    anomalies: List[QueueAnomalySummary]

class ModerationQueueResponse(BaseModel):
    items: List[ModerationQueueItem]
    total: int
    page: int
    size: int
