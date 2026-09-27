"""
Pydantic schemas for Student models (S1, S2).
Visible to admins only per database-schema.md §5 and D-07.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StudentCreate(BaseModel):
    roll_number: str = Field(..., min_length=1, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=150)
    department: Optional[str] = Field(None, max_length=100)


class StudentResponse(BaseModel):
    id: int
    roll_number: str
    full_name: str
    department: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentListResponse(BaseModel):
    items: List[StudentResponse]
    total: int
    page: int
    page_size: int
