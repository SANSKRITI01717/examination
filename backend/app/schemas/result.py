from pydantic import BaseModel
from typing import List, Optional

class ComputeResponse(BaseModel):
    computed: int

class ResultStudent(BaseModel):
    roll_number: Optional[str] = None
    full_name: Optional[str] = None

class ResultItem(BaseModel):
    id: int
    student: Optional[ResultStudent] = None  # Admin sees student info, Moderator might see anon_code or masked?
    anon_code: str
    total_marks: float
    max_marks: float
    percentage: float
    status: str

class ResultStats(BaseModel):
    mean: Optional[float] = None
    median: Optional[float] = None
    pass_rate: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None

class ResultListResponse(BaseModel):
    items: List[ResultItem]
    stats: ResultStats
    total: int

class QuestionBreakdown(BaseModel):
    question_number: str
    marks: float
    max_marks: float
    final_source: str

class ResultDetailResponse(BaseModel):
    result: ResultItem
    breakdown: List[QuestionBreakdown]

class PublishResponse(BaseModel):
    published: bool
