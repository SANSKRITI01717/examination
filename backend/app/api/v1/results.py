from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models.user import User
from app.schemas.result import ComputeResponse, ResultListResponse, ResultDetailResponse, PublishResponse
from app.services import result_service

router = APIRouter()

@router.post("/exams/{id}/results/compute", response_model=ComputeResponse)
def compute_results(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    """RS1: Compute totals from final_marks"""
    count = result_service.compute_results(db, id)
    return {"computed": count}

@router.get("/exams/{id}/results", response_model=ResultListResponse)
def list_results(
    id: int,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "moderator")),
):
    """RS2: List results and summary stats"""
    return result_service.get_results(db, id, page=page)

@router.get("/results/{id}", response_model=ResultDetailResponse)
def get_result_detail(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "moderator")),
):
    """RS3: Per-question breakdown"""
    return result_service.get_result_detail(db, id)

@router.post("/exams/{id}/results/publish", response_model=PublishResponse)
def publish_results(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    """RS4: Publish results"""
    published = result_service.publish_results(db, id)
    return {"published": published}
