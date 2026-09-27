from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case, text

from app.models.exam import Exam
from app.models.sheet import AnswerSheet
from app.models.answer import Answer
from app.models.question import Question
from app.models.student import Student
from app.models.result import Result
from app.models.anomaly import Anomaly
from app.core.errors import AppError

def compute_results(db: Session, exam_id: int) -> int:
    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(code="NOT_FOUND", status_code=404, message="Exam not found")
        
    if exam.status not in ["moderation", "completed"]:
        raise AppError(code="EXAM_NOT_READY", status_code=409, message="Exam must be in moderation or completed state")
        
    # Check for incomplete marking
    pending = db.scalar(select(func.count(Answer.id)).where(Answer.exam_id == exam_id, Answer.marking_status != "marked", Answer.marking_status != "moderated"))
    open_high = db.scalar(select(func.count(Anomaly.id)).where(Anomaly.exam_id == exam_id, Anomaly.status == "open", Anomaly.severity == "high"))
    
    if pending > 0 or open_high > 0:
        raise AppError(
            code="INCOMPLETE_MARKING",
            status_code=409,
            message="Cannot compute results. Marking incomplete or high severity anomalies open.",
            details={"pending": pending, "open_high_anomalies": open_high}
        )
        
    # Compute totals
    sheets = db.scalars(select(AnswerSheet).where(AnswerSheet.exam_id == exam_id)).all()
    count = 0
    for sheet in sheets:
        # Sum marks for this sheet
        answers = db.scalars(select(Answer).where(Answer.answer_sheet_id == sheet.id)).all()
        total_marks = sum(float(a.final_marks) for a in answers if a.final_marks is not None)
        
        # Max marks for the exam (sum of question max_marks)
        max_marks = db.scalar(select(func.sum(Question.max_marks)).where(Question.exam_id == exam_id))
        max_marks = float(max_marks) if max_marks else 0.0
        
        pct = (total_marks / max_marks * 100.0) if max_marks > 0 else 0.0
        
        # Upsert result
        res = db.scalar(select(Result).where(Result.exam_id == exam_id, Result.student_id == sheet.student_id))
        if not res:
            res = Result(exam_id=exam_id, student_id=sheet.student_id, status="draft")
            db.add(res)
            
        if res.status != "published":
            res.total_marks = total_marks
            res.max_marks = max_marks
            res.percentage = pct
            res.computed_at = func.now()
            count += 1
            
    db.commit()
    return count

def get_results(db: Session, exam_id: int, page: int = 1, limit: int = 50) -> Dict[str, Any]:
    offset = (page - 1) * limit
    
    q = select(Result, Student.roll_number, Student.full_name, AnswerSheet.anon_code).join(
        Student, Student.id == Result.student_id
    ).join(
        AnswerSheet, (AnswerSheet.exam_id == Result.exam_id) & (AnswerSheet.student_id == Result.student_id)
    ).where(Result.exam_id == exam_id)
    
    total = db.scalar(select(func.count(Result.id)).where(Result.exam_id == exam_id))
    rows = db.execute(q.offset(offset).limit(limit)).all()
    
    items = []
    for r in rows:
        items.append({
            "id": r.Result.id,
            "student": {
                "roll_number": r.roll_number,
                "full_name": r.full_name
            },
            "anon_code": r.anon_code,
            "total_marks": float(r.Result.total_marks),
            "max_marks": float(r.Result.max_marks),
            "percentage": float(r.Result.percentage),
            "status": r.Result.status
        })
        
    stats_q = select(
        func.avg(Result.total_marks).label("mean"),
        func.min(Result.total_marks).label("min_m"),
        func.max(Result.total_marks).label("max_m"),
        func.count(Result.id).label("total")
    ).where(Result.exam_id == exam_id)
    s_row = db.execute(stats_q).first()
    
    stats = {
        "mean": float(s_row.mean) if s_row and s_row.mean is not None else None,
        "median": None, # Complex to compute in basic Postgres efficiently, optional
        "pass_rate": None,
        "min": float(s_row.min_m) if s_row and s_row.min_m is not None else None,
        "max": float(s_row.max_m) if s_row and s_row.max_m is not None else None
    }
    
    return {"items": items, "stats": stats, "total": total or 0}

def get_result_detail(db: Session, result_id: int) -> Dict[str, Any]:
    res = db.get(Result, result_id)
    if not res:
        raise AppError(code="NOT_FOUND", status_code=404, message="Result not found")
        
    student = db.get(Student, res.student_id)
    sheet = db.scalar(select(AnswerSheet).where(AnswerSheet.exam_id == res.exam_id, AnswerSheet.student_id == res.student_id))
    
    item = {
        "id": res.id,
        "student": {
            "roll_number": student.roll_number,
            "full_name": student.full_name
        } if student else None,
        "anon_code": sheet.anon_code if sheet else "",
        "total_marks": float(res.total_marks),
        "max_marks": float(res.max_marks),
        "percentage": float(res.percentage),
        "status": res.status
    }
    
    # Breakdown
    breakdown = []
    if sheet:
        answers = db.scalars(select(Answer).where(Answer.answer_sheet_id == sheet.id)).all()
        for a in answers:
            q = db.get(Question, a.question_id)
            if q:
                breakdown.append({
                    "question_number": q.question_number,
                    "marks": float(a.final_marks) if a.final_marks is not None else 0.0,
                    "max_marks": float(q.max_marks),
                    "final_source": a.final_source or ""
                })
                
    return {"result": item, "breakdown": breakdown}

def publish_results(db: Session, exam_id: int) -> bool:
    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(code="NOT_FOUND", status_code=404, message="Exam not found")
        
    results = db.scalars(select(Result).where(Result.exam_id == exam_id, Result.status == "draft")).all()
    if not results:
        total = db.scalar(select(func.count(Result.id)).where(Result.exam_id == exam_id))
        if total == 0:
            raise AppError(code="RESULTS_NOT_COMPUTED", status_code=409, message="Results not computed yet")
        # If all published, we still mark exam as completed
    
    for r in results:
        r.status = "published"
        r.published_at = func.now()
        
    exam.status = "completed"
    db.commit()
    return True
