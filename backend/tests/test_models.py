"""
Tests for SQLAlchemy model definitions and database schema invariants.
"""
import pytest
from app.core.db import Base
import app.models  # noqa: F401


def test_all_models_registered_in_metadata():
    """Verify that all 15 tables are mapped into Base.metadata."""
    expected_tables = {
        "users",
        "students",
        "exams",
        "questions",
        "rubrics",
        "answer_sheets",
        "answer_sheet_pages",
        "answers",
        "ai_evaluations",
        "evaluations",
        "moderations",
        "anomalies",
        "reference_documents",
        "results",
        "ai_summaries",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"


def test_user_model_columns():
    users_table = Base.metadata.tables["users"]
    assert "id" in users_table.c
    assert "email" in users_table.c
    assert "password_hash" in users_table.c
    assert "role" in users_table.c
    assert "is_active" in users_table.c


def test_ai_evaluation_model_columns():
    ai_table = Base.metadata.tables["ai_evaluations"]
    assert "input_hash" in ai_table.c
    assert "suggested_marks" in ai_table.c
    assert "confidence" in ai_table.c
    assert "criteria" in ai_table.c
    assert "warnings" in ai_table.c
