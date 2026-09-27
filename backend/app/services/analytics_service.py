from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case, text

from app.models.exam import Exam
from app.models.sheet import AnswerSheet
from app.models.answer import Answer
from app.models.evaluation import Evaluation
from app.models.question import Question
from app.models.user import User
from app.models.anomaly import Anomaly
from app.core.errors import AppError

def get_overview(db: Session, exam_id: int) -> Dict[str, Any]:
    # Total answers for this exam
    q = select(
        func.count(Answer.id).label("total"),
        func.sum(case((Answer.ocr_status == "done", 1), else_=0)).label("ocr_done"),
        func.sum(case((Answer.ai_status == "done", 1), else_=0)).label("ai_done"),
        func.sum(case((Answer.marking_status == "marked", 1), else_=0)).label("marked"),
        func.sum(case((Answer.marking_status == "flagged", 1), else_=0)).label("flagged"),
        func.sum(case((Answer.marking_status == "moderated", 1), else_=0)).label("moderated"),
        func.sum(case((Answer.marking_status == "pending", 1), else_=0)).label("unchecked"),
    ).where(Answer.exam_id == exam_id)
    
    res = db.execute(q).first()
    
    total = res.total or 0
    
    # Low confidence OCR: Placeholder for now
    
    # Avg seconds per answer: from evaluations
    avg_q = select(func.avg(Evaluation.active_seconds)).join(Answer).where(Answer.exam_id == exam_id)
    avg_sec = db.scalar(avg_q)
    
    return {
        "answers_total": total,
        "ocr_done": res.ocr_done or 0,
        "ai_done": res.ai_done or 0,
        "marked": res.marked or 0,
        "flagged": res.flagged or 0,
        "moderated": res.moderated or 0,
        "unchecked": res.unchecked or 0,
        "low_ocr_confidence": 0, # Placeholder
        "avg_seconds_per_answer": float(avg_sec) if avg_sec else None
    }

def get_examiner_stats(db: Session, exam_id: int) -> List[Dict[str, Any]]:
    q = select(
        Answer.assigned_examiner_id,
        User.full_name,
        func.count(Answer.id).label("total"),
        func.sum(case((Answer.marking_status.in_(["marked", "moderated"]), 1), else_=0)).label("marked"),
        func.avg(Answer.final_marks).label("mean"),
        func.stddev(Answer.final_marks).label("sd"),
        func.sum(case((Answer.marking_status == "flagged", 1), else_=0)).label("flags")
    ).join(User, User.id == Answer.assigned_examiner_id).where(
        Answer.exam_id == exam_id, Answer.assigned_examiner_id.isnot(None)
    ).group_by(Answer.assigned_examiner_id, User.full_name)
    
    rows = db.execute(q).all()
    result = []
    
    global_mean = db.scalar(select(func.avg(Answer.final_marks)).where(Answer.exam_id == exam_id, Answer.marking_status.in_(["marked", "moderated"])))
    
    for r in rows:
        eval_q = select(
            func.avg(Evaluation.active_seconds).label("avg_sec"),
            func.sum(case((Evaluation.source == "ai_accepted", 1), else_=0)).label("ai_accepted"),
            func.sum(case((Evaluation.source == "ai_modified", 1), else_=0)).label("ai_modified"),
            func.sum(case((Evaluation.source == "manual", 1), else_=0)).label("manual"),
            func.count(Evaluation.id).label("total_evals")
        ).join(Answer).where(Answer.exam_id == exam_id, Evaluation.examiner_id == r.assigned_examiner_id, Evaluation.status == "submitted")
        
        eval_stats = db.execute(eval_q).first()
        
        total_evals = eval_stats.total_evals or 0
        pct_accepted = (eval_stats.ai_accepted / total_evals * 100) if total_evals > 0 else 0.0
        pct_modified = (eval_stats.ai_modified / total_evals * 100) if total_evals > 0 else 0.0
        pct_manual = (eval_stats.manual / total_evals * 100) if total_evals > 0 else 0.0
        
        result.append({
            "examiner": r.full_name,
            "examiner_id": r.assigned_examiner_id,
            "marked": r.marked or 0,
            "mean": float(r.mean) if r.mean is not None else None,
            "sd": float(r.sd) if r.sd is not None else None,
            "mean_vs_global": (float(r.mean) - float(global_mean)) if r.mean is not None and global_mean is not None else None,
            "avg_seconds": float(eval_stats.avg_sec) if eval_stats.avg_sec is not None else None,
            "pct_ai_accepted": float(pct_accepted),
            "pct_ai_modified": float(pct_modified),
            "pct_manual": float(pct_manual),
            "flags": r.flags or 0
        })
        
    return result

def get_question_stats(db: Session, exam_id: int) -> List[Dict[str, Any]]:
    q = select(
        Question.id,
        Question.question_number,
        func.avg(Answer.final_marks).label("mean"),
        func.stddev(Answer.final_marks).label("sd"),
        func.min(Answer.final_marks).label("min_m"),
        func.max(Answer.final_marks).label("max_m")
    ).outerjoin(Answer, (Answer.question_id == Question.id) & (Answer.marking_status.in_(["marked", "moderated"]))).where(
        Question.exam_id == exam_id
    ).group_by(Question.id, Question.question_number)
    
    rows = db.execute(q).all()
    result = []
    for r in rows:
        hist_q = select(Answer.final_marks, func.count(Answer.id).label("cnt")).where(
            Answer.question_id == r.id, Answer.marking_status.in_(["marked", "moderated"])
        ).group_by(Answer.final_marks).order_by(Answer.final_marks)
        
        hist_rows = db.execute(hist_q).all()
        histogram = [{"bucket": str(float(hr.final_marks)), "count": hr.cnt} for hr in hist_rows if hr.final_marks is not None]
        
        result.append({
            "question_id": r.id,
            "question_number": r.question_number,
            "mean": float(r.mean) if r.mean is not None else None,
            "sd": float(r.sd) if r.sd is not None else None,
            "min": float(r.min_m) if r.min_m is not None else None,
            "max": float(r.max_m) if r.max_m is not None else None,
            "histogram": histogram
        })
        
    return result

def get_my_progress(db: Session, exam_id: int, examiner_id: int) -> Dict[str, Any]:
    q = select(
        func.count(Answer.id).label("assigned"),
        func.sum(case((Answer.marking_status.in_(["marked", "moderated"]), 1), else_=0)).label("marked"),
        func.sum(case((Answer.marking_status == "flagged", 1), else_=0)).label("review_required")
    ).where(Answer.exam_id == exam_id, Answer.assigned_examiner_id == examiner_id)
    
    res = db.execute(q).first()
    
    avg_q = select(func.avg(Evaluation.active_seconds)).join(Answer).where(
        Answer.exam_id == exam_id, Evaluation.examiner_id == examiner_id
    )
    avg_sec = db.scalar(avg_q)
    
    assigned = res.assigned or 0
    marked = res.marked or 0
    review_required = res.review_required or 0
    remaining = assigned - marked - review_required
    
    return {
        "assigned": assigned,
        "marked": marked,
        "remaining": max(remaining, 0),
        "review_required": review_required,
        "avg_seconds": float(avg_sec) if avg_sec else None
    }
