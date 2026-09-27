"""
Answer Sheet, Page Mapping, Page Image Streaming & Assignment API (AS1-AS6).
Contract: api-spec.md §7.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_role
from app.core.storage import get_storage
from app.core.storage.base import StorageService
from app.models.user import User
from app.schemas.sheet import (
    AnswerSheetDetailResponse,
    AnswerSheetListResponse,
    AnswerSheetResponse,
    AnswerSummary,
    AssignmentRequest,
    AssignmentResponse,
    MappingRequest,
)
from app.services import sheet_service

router = APIRouter(tags=["Answer Sheets, Mapping & Assignments"])


@router.post(
    "/exams/{id}/answer-sheets",
    response_model=AnswerSheetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_answer_sheet_endpoint(
    id: int,
    student_id: int = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
    storage: StorageService = Depends(get_storage),
):
    """AS1: Upload a student's answer sheet (PDF or JPEG/PNG pages)."""
    sheet = await sheet_service.upload_sheet(
        db=db,
        exam_id=id,
        student_id=student_id,
        files=files,
        user_id=current_user.id,
        storage=storage,
    )
    return AnswerSheetResponse(
        id=sheet.id,
        exam_id=sheet.exam_id,
        student_id=sheet.student_id,
        anon_code=sheet.anon_code,
        status=sheet.status,
        page_count=len(sheet.pages) if hasattr(sheet, "pages") and sheet.pages else 0,
        created_at=sheet.created_at,
    )


@router.get("/exams/{id}/answer-sheets", response_model=AnswerSheetListResponse)
def list_answer_sheets_endpoint(
    id: int,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """AS2: List answer sheets with progress (Admin only)."""
    items, total = sheet_service.get_sheets(
        db, exam_id=id, status=status, page=page, page_size=page_size, is_admin=True
    )
    return AnswerSheetListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/answer-sheets/{id}", response_model=AnswerSheetDetailResponse)
def get_answer_sheet_detail_endpoint(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AS3: Get answer sheet detail, pages, and answers (role-aware blind marking)."""
    return sheet_service.get_sheet_detail(db, id, current_user)


@router.put("/answer-sheets/{id}/mapping", response_model=List[AnswerSummary])
def map_page_ranges_endpoint(
    id: int,
    data: MappingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """AS4: Map page ranges to questions; sets sheet status to mapped."""
    answers = sheet_service.map_pages(db, id, data.items)
    # Build summaries
    summaries: List[AnswerSummary] = []
    for a in answers:
        summaries.append(
            AnswerSummary(
                id=a.id,
                question_id=a.question_id,
                question_number=a.question.question_number if hasattr(a, "question") and a.question else str(a.question_id),
                page_start=a.page_start,
                page_end=a.page_end,
                is_attempted=a.is_attempted,
                ocr_status=a.ocr_status,
                ai_status=a.ai_status,
                marking_status=a.marking_status,
                final_marks=float(a.final_marks) if a.final_marks is not None else None,
                max_marks=float(a.question.max_marks) if hasattr(a, "question") and a.question else 10.0,
            )
        )
    return summaries


@router.get("/pages/{page_id}/image")
def stream_page_image_endpoint(
    page_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage),
):
    """AS5: Stream a page image (authorized for admin, assigned examiner, or moderator)."""
    data, content_type = sheet_service.get_page_image(db, page_id, current_user, storage)
    return Response(content=data, media_type=content_type)


@router.post("/exams/{id}/assignments", response_model=AssignmentResponse)
def assign_examiners_endpoint(
    id: int,
    data: AssignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """AS6: Assign unmarked answers to examiners (by_sheet or by_question)."""
    return sheet_service.assign_examiners(db, id, data.examiner_ids, data.strategy)
