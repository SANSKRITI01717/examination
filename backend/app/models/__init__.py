"""
Import all models so that Base.metadata is fully populated.
Alembic's env.py imports Base from app.core.db; this file must be imported first
so that all table definitions are registered before autogenerate runs.

Import order respects foreign key dependencies (referenced tables first).
"""
from app.models.user import User  # noqa: F401 — no FKs
from app.models.student import Student  # noqa: F401 — no FKs
from app.models.exam import Exam  # noqa: F401 — FK: users
from app.models.question import Question, Rubric  # noqa: F401 — FK: exams
from app.models.sheet import AnswerSheet, AnswerSheetPage  # noqa: F401 — FK: exams, students, users
from app.models.answer import Answer  # noqa: F401 — FK: exams, answer_sheets, questions, users
from app.models.evaluation import AIEvaluation, Evaluation  # noqa: F401 — FK: answers, users
from app.models.moderation import Moderation  # noqa: F401 — FK: answers, evaluations, users
from app.models.anomaly import Anomaly  # noqa: F401 — FK: exams, answers, questions, users
from app.models.reference import ReferenceDocument  # noqa: F401 — FK: exams, questions, users
from app.models.result import Result  # noqa: F401 — FK: exams, students
from app.models.summary import AISummary  # noqa: F401 — FK: exams, users

__all__ = [
    "User",
    "Student",
    "Exam",
    "Question",
    "Rubric",
    "AnswerSheet",
    "AnswerSheetPage",
    "Answer",
    "AIEvaluation",
    "Evaluation",
    "Moderation",
    "Anomaly",
    "ReferenceDocument",
    "Result",
    "AISummary",
]
