"""
Question & Rubric service — business logic and validation for questions and rubrics.
Enforces rules from api-spec.md §5 and architecture.md §5.
"""
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models.answer import Answer
from app.models.exam import Exam
from app.models.question import Question, Rubric
from app.schemas.question import QuestionCreate, QuestionUpdate, RubricCreate


def create_question(db: Session, exam_id: int, data: QuestionCreate) -> Question:
    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(
            code="NOT_FOUND",
            message=f"Exam with id {exam_id} not found",
            status_code=404,
        )

    if exam.status != "draft":
        raise AppError(
            code="EXAM_LOCKED",
            message="Questions can only be added to draft exams",
            status_code=409,
        )

    existing = db.scalar(
        select(Question).where(
            Question.exam_id == exam_id,
            Question.question_number == data.question_number,
        )
    )
    if existing:
        raise AppError(
            code="DUPLICATE_QUESTION_NUMBER",
            message=f"Question number '{data.question_number}' already exists in this exam",
            status_code=409,
        )

    question = Question(
        exam_id=exam_id,
        question_number=data.question_number,
        text=data.text,
        max_marks=data.max_marks,
        evaluation_mode=data.evaluation_mode or "standard",
        display_order=data.display_order or 0,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def get_questions_for_exam(db: Session, exam_id: int) -> List[Question]:
    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(
            code="NOT_FOUND",
            message=f"Exam with id {exam_id} not found",
            status_code=404,
        )

    stmt = (
        select(Question)
        .where(Question.exam_id == exam_id)
        .options(joinedload(Question.rubric))
        .order_by(Question.display_order.asc(), Question.id.asc())
    )
    return list(db.scalars(stmt).unique().all())


def get_question_by_id(db: Session, question_id: int) -> Question:
    stmt = (
        select(Question)
        .where(Question.id == question_id)
        .options(joinedload(Question.rubric))
    )
    question = db.scalar(stmt)
    if not question:
        raise AppError(
            code="NOT_FOUND",
            message=f"Question with id {question_id} not found",
            status_code=404,
        )
    return question


def update_question(
    db: Session, question_id: int, data: QuestionUpdate
) -> Question:
    question = get_question_by_id(db, question_id)
    exam = db.get(Exam, question.exam_id)

    if not exam or exam.status != "draft":
        raise AppError(
            code="EXAM_LOCKED",
            message="Questions can only be edited in draft exams",
            status_code=409,
        )

    if data.question_number is not None and data.question_number != question.question_number:
        existing = db.scalar(
            select(Question).where(
                Question.exam_id == question.exam_id,
                Question.question_number == data.question_number,
                Question.id != question_id,
            )
        )
        if existing:
            raise AppError(
                code="DUPLICATE_QUESTION_NUMBER",
                message=f"Question number '{data.question_number}' already exists in this exam",
                status_code=409,
            )
        question.question_number = data.question_number

    if data.text is not None:
        question.text = data.text
    if data.max_marks is not None:
        question.max_marks = data.max_marks
    if data.evaluation_mode is not None:
        question.evaluation_mode = data.evaluation_mode
    if data.display_order is not None:
        question.display_order = data.display_order

    db.commit()
    db.refresh(question)
    return question


def delete_question(db: Session, question_id: int) -> None:
    question = get_question_by_id(db, question_id)
    exam = db.get(Exam, question.exam_id)

    if not exam or exam.status != "draft":
        raise AppError(
            code="EXAM_LOCKED",
            message="Questions can only be deleted in draft exams",
            status_code=409,
        )

    answer_count = db.scalar(
        select(func.count(Answer.id)).where(Answer.question_id == question_id)
    ) or 0
    if answer_count > 0:
        raise AppError(
            code="HAS_ANSWERS",
            message="Cannot delete question that has associated student answers",
            status_code=409,
        )

    db.delete(question)
    db.commit()


def upsert_rubric(db: Session, question_id: int, data: RubricCreate) -> Rubric:
    question = get_question_by_id(db, question_id)
    exam = db.get(Exam, question.exam_id)

    if not exam or exam.status != "draft":
        raise AppError(
            code="EXAM_LOCKED",
            message="Rubrics can only be edited in draft exams",
            status_code=409,
        )

    # 1. Unique criterion IDs
    ids = [c.id for c in data.criteria]
    if len(ids) != len(set(ids)):
        raise AppError(
            code="DUPLICATE_CRITERION_ID",
            message="Criterion IDs must be unique within a rubric",
            status_code=422,
        )

    # 2. Criteria sum must match question max_marks
    criteria_sum = sum(c.max_marks for c in data.criteria)
    if round(float(criteria_sum), 2) != round(float(question.max_marks), 2):
        raise AppError(
            code="RUBRIC_SUM_MISMATCH",
            message=f"Rubric criteria sum ({criteria_sum}) does not match question max marks ({question.max_marks})",
            status_code=422,
            details={
                "criteria_sum": criteria_sum,
                "max_marks": float(question.max_marks),
            },
        )

    criteria_json = [c.model_dump() for c in data.criteria]

    rubric = db.scalar(select(Rubric).where(Rubric.question_id == question_id))
    if rubric:
        rubric.criteria = criteria_json
        rubric.guidance = data.guidance
    else:
        rubric = Rubric(
            question_id=question_id,
            criteria=criteria_json,
            guidance=data.guidance,
        )
        db.add(rubric)

    db.commit()
    db.refresh(rubric)
    return rubric


def get_rubric(db: Session, question_id: int) -> Rubric:
    question = db.get(Question, question_id)
    if not question:
        raise AppError(
            code="NOT_FOUND",
            message=f"Question with id {question_id} not found",
            status_code=404,
        )

    rubric = db.scalar(select(Rubric).where(Rubric.question_id == question_id))
    if not rubric:
        raise AppError(
            code="NOT_FOUND",
            message=f"Rubric not found for question {question_id}",
            status_code=404,
        )
    return rubric
