"""
Service layer for anomalies.
"""
from typing import Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.anomaly import Anomaly
from app.models.exam import Exam
from app.models.user import User


def list_anomalies(
    db: Session,
    exam_id: int,
    user: User,
    anomaly_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    examiner_id: Optional[int] = None,
    question_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 25,
) -> Tuple[list, int]:
    
    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(code="NOT_FOUND", message="Exam not found", status_code=404)

    query = select(Anomaly).where(Anomaly.exam_id == exam_id)
    count_query = select(func.count()).where(Anomaly.exam_id == exam_id)

    if anomaly_type:
        query = query.where(Anomaly.type == anomaly_type)
        count_query = count_query.where(Anomaly.type == anomaly_type)
        
    if severity:
        query = query.where(Anomaly.severity == severity)
        count_query = count_query.where(Anomaly.severity == severity)
        
    if status:
        query = query.where(Anomaly.status == status)
        count_query = count_query.where(Anomaly.status == status)
        
    if examiner_id:
        query = query.where(Anomaly.examiner_id == examiner_id)
        count_query = count_query.where(Anomaly.examiner_id == examiner_id)
        
    if question_id:
        query = query.where(Anomaly.question_id == question_id)
        count_query = count_query.where(Anomaly.question_id == question_id)

    total = db.scalar(count_query) or 0
    items = db.scalars(
        query.order_by(Anomaly.detected_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    
    # serialize
    results = []
    for item in items:
        results.append({
            "id": item.id,
            "exam_id": item.exam_id,
            "type": item.type,
            "severity": item.severity,
            "answer_id": item.answer_id,
            "question_id": item.question_id,
            "examiner_id": item.examiner_id,
            "score": float(item.score) if item.score is not None else None,
            "details": item.details,
            "status": item.status,
            "note": item.note,
            "detected_at": item.detected_at.isoformat() if item.detected_at else None,
        })

    return results, total


def update_anomaly(db: Session, anomaly_id: int, user: User, status: str, note: Optional[str]) -> dict:
    anomaly = db.get(Anomaly, anomaly_id)
    if not anomaly:
        raise AppError(code="NOT_FOUND", message="Anomaly not found", status_code=404)
        
    if anomaly.status == "resolved":
        raise AppError(code="ALREADY_RESOLVED", message="Cannot change a resolved anomaly", status_code=409)

    anomaly.status = status
    if note is not None:
        anomaly.note = note
        
    db.commit()
    db.refresh(anomaly)
    
    return {
        "id": anomaly.id,
        "exam_id": anomaly.exam_id,
        "type": anomaly.type,
        "severity": anomaly.severity,
        "answer_id": anomaly.answer_id,
        "question_id": anomaly.question_id,
        "examiner_id": anomaly.examiner_id,
        "score": float(anomaly.score) if anomaly.score is not None else None,
        "details": anomaly.details,
        "status": anomaly.status,
        "note": anomaly.note,
        "detected_at": anomaly.detected_at.isoformat() if anomaly.detected_at else None,
    }
