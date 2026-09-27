"""
Tests for Anomaly detectors (AN1-AN3).
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.core.db import SessionLocal
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.anomaly import Anomaly
from app.models.exam import Exam
from app.models.user import User
from app.models.question import Question
from app.models.answer import Answer
from app.models.evaluation import Evaluation, AIEvaluation

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_anomaly_data():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "ano_admin@osm.local").first()
        if not admin:
            admin = User(
                email="ano_admin@osm.local",
                password_hash=hash_password("Pass123!"),
                full_name="Ano Admin",
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        exam = Exam(
            title="Anomaly Exam",
            course_code="ANO-101",
            status="moderation",
            settings={"too_fast_seconds": 10, "z_threshold": 2.5, "min_sample_size": 2, "ai_disagreement_ratio": 0.3},
            created_by=admin.id,
        )
        db.add(exam)
        db.commit()
        db.refresh(exam)

        admin_token, _ = create_access_token(admin.id, admin.role)

        # Create basic anomaly manually
        ano = Anomaly(
            exam_id=exam.id,
            type="UNCHECKED_ANSWER",
            severity="high",
            status="open",
            details={},
            dedupe_key="test_ano_1"
        )
        db.add(ano)
        db.commit()
        db.refresh(ano)

        return {
            "admin_token": admin_token,
            "exam_id": exam.id,
            "ano_id": ano.id
        }
    finally:
        db.close()


def test_list_anomalies(setup_anomaly_data):
    headers = {"Authorization": f"Bearer {setup_anomaly_data['admin_token']}"}
    res = client.get(f"/api/v1/exams/{setup_anomaly_data['exam_id']}/anomalies", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert data["items"][0]["type"] == "UNCHECKED_ANSWER"


def test_patch_anomaly(setup_anomaly_data):
    headers = {"Authorization": f"Bearer {setup_anomaly_data['admin_token']}"}
    res = client.patch(
        f"/api/v1/anomalies/{setup_anomaly_data['ano_id']}",
        json={"status": "dismissed", "note": "All good"},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "dismissed"
    assert data["note"] == "All good"


def test_patch_resolved_anomaly_fails(setup_anomaly_data):
    # Set to resolved manually
    db = SessionLocal()
    ano = db.get(Anomaly, setup_anomaly_data["ano_id"])
    ano.status = "resolved"
    db.commit()
    db.close()

    headers = {"Authorization": f"Bearer {setup_anomaly_data['admin_token']}"}
    res = client.patch(
        f"/api/v1/anomalies/{setup_anomaly_data['ano_id']}",
        json={"status": "open"},
        headers=headers
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "ALREADY_RESOLVED"


def test_run_anomalies_no_data(setup_anomaly_data):
    # Run detector on empty exam data
    headers = {"Authorization": f"Bearer {setup_anomaly_data['admin_token']}"}
    db = SessionLocal()
    exam2 = Exam(title="Empty", course_code="EMP-101", status="moderation", created_by=1)
    db.add(exam2)
    db.commit()
    db.refresh(exam2)
    db.close()

    res = client.post(f"/api/v1/exams/{exam2.id}/anomalies/detect", json={}, headers=headers)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "NOT_ENOUGH_DATA"


def test_detectors_pure_logic():
    from app.ai.anomaly.detectors import detect_unchecked_answers
    
    answers = [
        {"id": 1, "is_attempted": True, "marking_status": "pending", "assigned_examiner_id": 10},
        {"id": 2, "is_attempted": True, "marking_status": "marked", "assigned_examiner_id": 10},
        {"id": 3, "is_attempted": False, "marking_status": "pending", "assigned_examiner_id": 10},
    ]
    
    anos = detect_unchecked_answers(answers, "moderation")
    assert len(anos) == 1
    assert anos[0]["answer_id"] == 1
    assert anos[0]["type"] == "UNCHECKED_ANSWER"

