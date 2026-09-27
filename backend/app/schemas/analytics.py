from pydantic import BaseModel
from typing import List, Optional

class AnalyticsOverview(BaseModel):
    answers_total: int
    ocr_done: int
    ai_done: int
    marked: int
    flagged: int
    moderated: int
    unchecked: int
    low_ocr_confidence: int
    avg_seconds_per_answer: Optional[float] = None

class ExaminerStats(BaseModel):
    examiner: str
    examiner_id: int
    marked: int
    mean: Optional[float] = None
    sd: Optional[float] = None
    mean_vs_global: Optional[float] = None
    avg_seconds: Optional[float] = None
    pct_ai_accepted: float
    pct_ai_modified: float
    pct_manual: float
    flags: int

class HistogramBucket(BaseModel):
    bucket: str
    count: int

class QuestionStats(BaseModel):
    question_id: int
    question_number: str
    mean: Optional[float] = None
    sd: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    histogram: List[HistogramBucket]

class ExaminerProgress(BaseModel):
    assigned: int
    marked: int
    remaining: int
    review_required: int
    avg_seconds: Optional[float] = None
