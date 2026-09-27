"""
Answer Sheet, Page Mapping & Examiner Assignment Service (AS1-AS6).
Enforces rules from api-spec.md §7, architecture.md §4, §5, and database-schema.md §6, §7.
"""
import io
import secrets
from typing import Any, Dict, List, Optional, Tuple
import pymupdf as fitz
from PIL import Image
from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.errors import AppError
from app.core.storage.base import StorageService
from app.models.answer import Answer
from app.models.exam import Exam
from app.models.question import Question
from app.models.sheet import AnswerSheet, AnswerSheetPage
from app.models.student import Student
from app.models.user import User
from app.schemas.sheet import AssignmentStrategyType, MappingItem


def generate_anon_code(db: Session, exam_id: int) -> str:
    """Generate unique anon_code for blind marking per exam."""
    for _ in range(100):
        code = f"S-{secrets.randbelow(90000) + 10000}"
        existing = db.scalar(
            select(AnswerSheet).where(
                AnswerSheet.exam_id == exam_id,
                AnswerSheet.anon_code == code,
            )
        )
        if not existing:
            return code
    raise RuntimeError("Failed to generate unique anon_code")


async def upload_sheet(
    db: Session,
    exam_id: int,
    student_id: int,
    files: List[UploadFile],
    user_id: int,
    storage: StorageService,
) -> AnswerSheet:
    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(code="NOT_FOUND", message=f"Exam {exam_id} not found", status_code=404)

    if exam.status in ("moderation", "completed"):
        raise AppError(
            code="EXAM_LOCKED",
            message="Answer sheets cannot be uploaded to an exam in moderation or completed state",
            status_code=409,
        )

    student = db.get(Student, student_id)
    if not student:
        raise AppError(code="NOT_FOUND", message=f"Student {student_id} not found", status_code=404)

    existing_sheet = db.scalar(
        select(AnswerSheet).where(
            AnswerSheet.exam_id == exam_id,
            AnswerSheet.student_id == student_id,
        )
    )
    if existing_sheet:
        raise AppError(
            code="SHEET_EXISTS",
            message=f"An answer sheet for student #{student_id} already exists in this exam",
            status_code=409,
        )

    if not files:
        raise AppError(code="VALIDATION_ERROR", message="No files provided", status_code=422)

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    file_bytes_list: List[Tuple[str, bytes]] = []

    for f in files:
        content = await f.read()
        if len(content) > max_bytes:
            raise AppError(
                code="FILE_TOO_LARGE",
                message=f"File {f.filename} exceeds maximum size of {settings.MAX_UPLOAD_MB}MB",
                status_code=413,
            )
        filename = (f.filename or "").lower()
        file_bytes_list.append((filename, content))

    anon_code = generate_anon_code(db, exam_id)
    sheet = AnswerSheet(
        exam_id=exam_id,
        student_id=student_id,
        anon_code=anon_code,
        status="uploaded",
        uploaded_by=user_id,
    )
    db.add(sheet)
    db.flush()

    page_number = 1

    # Check if single PDF
    if len(file_bytes_list) == 1 and file_bytes_list[0][0].endswith(".pdf"):
        pdf_bytes = file_bytes_list[0][1]
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for i in range(len(doc)):
                page = doc[i]
                pix = page.get_pixmap(dpi=150)
                img_data = pix.tobytes("jpeg")

                storage_key = f"sheets/{exam_id}/{sheet.id}/page_{page_number}.jpg"
                storage.save(storage_key, img_data, content_type="image/jpeg")

                sheet_page = AnswerSheetPage(
                    answer_sheet_id=sheet.id,
                    page_number=page_number,
                    storage_key=storage_key,
                    width=pix.width,
                    height=pix.height,
                )
                db.add(sheet_page)
                page_number += 1
            doc.close()
        except Exception as e:
            raise AppError(
                code="UNSUPPORTED_FILE",
                message=f"Failed to process PDF document: {str(e)}",
                status_code=415,
            )
    else:
        # Image files: JPEG / PNG
        # Sort by filename to guarantee predictable page order
        file_bytes_list.sort(key=lambda x: x[0])
        for filename, content in file_bytes_list:
            if not (filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png")):
                raise AppError(
                    code="UNSUPPORTED_FILE",
                    message=f"Unsupported file type for '{filename}'. Allowed: PDF, JPG, PNG",
                    status_code=415,
                )
            try:
                img = Image.open(io.BytesIO(content))
                img_format = img.format
                width, height = img.size

                # Convert RGBA / P mode to RGB for consistent JPEG storage
                if img.mode != "RGB":
                    img = img.convert("RGB")
                out_io = io.BytesIO()
                img.save(out_io, format="JPEG", quality=85)
                img_data = out_io.getvalue()

                storage_key = f"sheets/{exam_id}/{sheet.id}/page_{page_number}.jpg"
                storage.save(storage_key, img_data, content_type="image/jpeg")

                sheet_page = AnswerSheetPage(
                    answer_sheet_id=sheet.id,
                    page_number=page_number,
                    storage_key=storage_key,
                    width=width,
                    height=height,
                )
                db.add(sheet_page)
                page_number += 1
            except Exception as e:
                raise AppError(
                    code="UNSUPPORTED_FILE",
                    message=f"Corrupted or invalid image '{filename}': {str(e)}",
                    status_code=415,
                )

    db.commit()
    db.refresh(sheet)
    return sheet


def get_sheets(
    db: Session,
    exam_id: int,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
    is_admin: bool = True,
) -> Tuple[List[Dict[str, Any]], int]:
    stmt = select(AnswerSheet).where(AnswerSheet.exam_id == exam_id)
    if status:
        stmt = stmt.where(AnswerSheet.status == status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    sheets = list(
        db.scalars(
            stmt.order_by(AnswerSheet.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )

    items: List[Dict[str, Any]] = []
    for sheet in sheets:
        page_count = db.scalar(
            select(func.count(AnswerSheetPage.id)).where(
                AnswerSheetPage.answer_sheet_id == sheet.id
            )
        ) or 0
        answers_total = db.scalar(
            select(func.count(Answer.id)).where(Answer.answer_sheet_id == sheet.id)
        ) or 0
        answers_marked = db.scalar(
            select(func.count(Answer.id)).where(
                Answer.answer_sheet_id == sheet.id,
                Answer.marking_status.in_(["marked", "moderated"]),
            )
        ) or 0

        student_data = None
        if is_admin:
            student = db.get(Student, sheet.student_id)
            if student:
                student_data = {
                    "id": student.id,
                    "roll_number": student.roll_number,
                    "full_name": student.full_name,
                    "department": student.department,
                    "created_at": student.created_at,
                }

        items.append({
            "id": sheet.id,
            "exam_id": sheet.exam_id,
            "student_id": sheet.student_id if is_admin else None,
            "anon_code": sheet.anon_code,
            "status": sheet.status,
            "page_count": page_count,
            "created_at": sheet.created_at,
            "student": student_data,
            "mapped": sheet.status == "mapped",
            "answers_total": answers_total,
            "answers_marked": answers_marked,
        })

    return items, total


def get_sheet_detail(db: Session, sheet_id: int, current_user: User) -> Dict[str, Any]:
    sheet = db.get(AnswerSheet, sheet_id)
    if not sheet:
        raise AppError(code="NOT_FOUND", message=f"Sheet {sheet_id} not found", status_code=404)

    pages = list(
        db.scalars(
            select(AnswerSheetPage)
            .where(AnswerSheetPage.answer_sheet_id == sheet_id)
            .order_by(AnswerSheetPage.page_number.asc())
        ).all()
    )

    # Answers query
    ans_stmt = (
        select(Answer, Question)
        .join(Question, Question.id == Answer.question_id)
        .where(Answer.answer_sheet_id == sheet_id)
        .order_by(Question.display_order.asc(), Question.id.asc())
    )

    if current_user.role == "examiner":
        ans_stmt = ans_stmt.where(Answer.assigned_examiner_id == current_user.id)

    results = db.execute(ans_stmt).all()

    if current_user.role == "examiner" and not results:
        # Check if examiner has ANY answers on this sheet
        has_any = db.scalar(
            select(func.count(Answer.id)).where(
                Answer.answer_sheet_id == sheet_id,
                Answer.assigned_examiner_id == current_user.id,
            )
        )
        if not has_any:
            raise AppError(code="FORBIDDEN", message="You do not have access to this answer sheet", status_code=403)

    answers_list = []
    answers_marked = 0
    for ans, q in results:
        if ans.marking_status in ("marked", "moderated"):
            answers_marked += 1
        answers_list.append({
            "id": ans.id,
            "question_id": q.id,
            "question_number": q.question_number,
            "page_start": ans.page_start,
            "page_end": ans.page_end,
            "is_attempted": ans.is_attempted,
            "ocr_status": ans.ocr_status,
            "ai_status": ans.ai_status,
            "marking_status": ans.marking_status,
            "final_marks": float(ans.final_marks) if ans.final_marks is not None else None,
            "max_marks": float(q.max_marks),
        })

    student_data = None
    if current_user.role == "admin":
        student = db.get(Student, sheet.student_id)
        if student:
            student_data = {
                "id": student.id,
                "roll_number": student.roll_number,
                "full_name": student.full_name,
                "department": student.department,
                "created_at": student.created_at,
            }

    pages_list = [
        {
            "id": p.id,
            "sheet_id": p.answer_sheet_id,
            "page_number": p.page_number,
            "image_url": f"/api/v1/pages/{p.id}/image",
            "width": p.width,
            "height": p.height,
        }
        for p in pages
    ]

    return {
        "id": sheet.id,
        "exam_id": sheet.exam_id,
        "student_id": sheet.student_id if current_user.role == "admin" else None,
        "anon_code": sheet.anon_code,
        "status": sheet.status,
        "page_count": len(pages),
        "created_at": sheet.created_at,
        "student": student_data,
        "mapped": sheet.status == "mapped",
        "answers_total": len(answers_list),
        "answers_marked": answers_marked,
        "pages": pages_list,
        "answers": answers_list,
    }


def map_pages(
    db: Session, sheet_id: int, items: List[MappingItem]
) -> List[Answer]:
    sheet = db.get(AnswerSheet, sheet_id)
    if not sheet:
        raise AppError(code="NOT_FOUND", message=f"Sheet {sheet_id} not found", status_code=404)

    exam = db.get(Exam, sheet.exam_id)
    if not exam or exam.status == "completed":
        raise AppError(
            code="EXAM_LOCKED",
            message="Cannot map pages on a completed exam",
            status_code=409,
        )

    page_count = db.scalar(
        select(func.count(AnswerSheetPage.id)).where(
            AnswerSheetPage.answer_sheet_id == sheet_id
        )
    ) or 0

    if page_count == 0:
        raise AppError(
            code="PAGE_RANGE_INVALID",
            message="This answer sheet has no pages uploaded",
            status_code=422,
        )

    # Validate each item
    for item in items:
        if not (1 <= item.page_start <= item.page_end <= page_count):
            raise AppError(
                code="PAGE_RANGE_INVALID",
                message=f"Page range ({item.page_start}-{item.page_end}) is invalid. Sheet has {page_count} pages",
                status_code=422,
                details={"page_start": item.page_start, "page_end": item.page_end, "page_count": page_count},
            )

        q = db.get(Question, item.question_id)
        if not q or q.exam_id != sheet.exam_id:
            raise AppError(
                code="NOT_FOUND",
                message=f"Question {item.question_id} not found in this exam",
                status_code=404,
            )

        existing = db.scalar(
            select(Answer).where(
                Answer.answer_sheet_id == sheet_id,
                Answer.question_id == item.question_id,
            )
        )
        if existing and existing.marking_status in ("marked", "moderated"):
            raise AppError(
                code="ANSWER_ALREADY_MARKED",
                message=f"Question {q.question_number} has already been marked and cannot be re-mapped",
                status_code=409,
            )

    saved_answers: List[Answer] = []

    for item in items:
        ans = db.scalar(
            select(Answer).where(
                Answer.answer_sheet_id == sheet_id,
                Answer.question_id == item.question_id,
            )
        )
        if not ans:
            ans = Answer(
                exam_id=sheet.exam_id,
                answer_sheet_id=sheet_id,
                question_id=item.question_id,
            )
            db.add(ans)

        ans.page_start = item.page_start
        ans.page_end = item.page_end
        ans.is_attempted = item.is_attempted

        if not item.is_attempted:
            ans.final_marks = 0.0
            ans.final_source = "system"
            ans.marking_status = "marked"
            ans.ocr_status = "done"
            ans.ai_status = "done"

        saved_answers.append(ans)

    sheet.status = "mapped"
    db.commit()
    for ans in saved_answers:
        db.refresh(ans)

    return saved_answers


def assign_examiners(
    db: Session,
    exam_id: int,
    examiner_ids: List[int],
    strategy: AssignmentStrategyType,
) -> Dict[str, Any]:
    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(code="NOT_FOUND", message=f"Exam {exam_id} not found", status_code=404)

    # 1. Validate examiners
    examiners = list(
        db.scalars(
            select(User).where(
                User.id.in_(examiner_ids),
                User.role == "examiner",
                User.is_active.is_(True),
            )
        ).all()
    )
    valid_ids = {e.id for e in examiners}
    invalid_ids = set(examiner_ids) - valid_ids
    if invalid_ids:
        raise AppError(
            code="NOT_AN_EXAMINER",
            message=f"User IDs {list(invalid_ids)} are not active examiners",
            status_code=422,
        )

    # 2. Check mapped sheets exist
    mapped_count = db.scalar(
        select(func.count(AnswerSheet.id)).where(
            AnswerSheet.exam_id == exam_id,
            AnswerSheet.status == "mapped",
        )
    ) or 0
    if mapped_count == 0:
        raise AppError(
            code="NO_MAPPED_SHEETS",
            message="Cannot assign examiners: no mapped answer sheets exist for this exam",
            status_code=409,
        )

    # 3. Find unassigned answers (or unmarked answers)
    unassigned_answers = list(
        db.scalars(
            select(Answer)
            .where(
                Answer.exam_id == exam_id,
                Answer.marking_status == "pending",
            )
            .order_by(Answer.answer_sheet_id.asc(), Answer.question_id.asc())
        ).all()
    )

    per_examiner: Dict[str, int] = {str(eid): 0 for eid in examiner_ids}

    if not unassigned_answers:
        return {"assigned": 0, "per_examiner": per_examiner}

    num_examiners = len(examiner_ids)

    if strategy == "by_sheet":
        # Group answers by answer_sheet_id
        sheets_answers: Dict[int, List[Answer]] = {}
        for ans in unassigned_answers:
            sheets_answers.setdefault(ans.answer_sheet_id, []).append(ans)

        for idx, (sheet_id, ans_group) in enumerate(sheets_answers.items()):
            assigned_eid = examiner_ids[idx % num_examiners]
            for ans in ans_group:
                ans.assigned_examiner_id = assigned_eid
                per_examiner[str(assigned_eid)] += 1
    else:  # by_question
        for idx, ans in enumerate(unassigned_answers):
            assigned_eid = examiner_ids[idx % num_examiners]
            ans.assigned_examiner_id = assigned_eid
            per_examiner[str(assigned_eid)] += 1

    db.commit()

    return {
        "assigned": len(unassigned_answers),
        "per_examiner": per_examiner,
    }


def get_page_image(
    db: Session,
    page_id: int,
    current_user: User,
    storage: StorageService,
) -> Tuple[bytes, str]:
    page = db.get(AnswerSheetPage, page_id)
    if not page:
        raise AppError(code="NOT_FOUND", message=f"Page {page_id} not found", status_code=404)

    sheet = db.get(AnswerSheet, page.answer_sheet_id)
    if not sheet:
        raise AppError(code="NOT_FOUND", message="Associated answer sheet not found", status_code=404)

    # RBAC check
    if current_user.role == "examiner":
        is_assigned = db.scalar(
            select(func.count(Answer.id)).where(
                Answer.answer_sheet_id == sheet.id,
                Answer.assigned_examiner_id == current_user.id,
            )
        )
        if not is_assigned:
            raise AppError(code="FORBIDDEN", message="You do not have access to view this page image", status_code=403)

    try:
        data = storage.get(page.storage_key)
        return data, "image/jpeg"
    except FileNotFoundError:
        raise AppError(code="NOT_FOUND", message="Image file not found in storage", status_code=404)
