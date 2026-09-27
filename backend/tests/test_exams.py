"""
Tests for Exams, Questions, and Rubrics endpoints (E1-E5, Q1-Q4, R1-R2).
"""
import pytest
from fastapi.testclient import TestClient

from app.core.db import SessionLocal
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.exam import Exam
from app.models.question import Question, Rubric
from app.models.user import User

client = TestClient(app)


@pytest.fixture(scope="module")
def auth_tokens():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "exam_admin@osm.local").first()
        if not admin:
            admin = User(
                email="exam_admin@osm.local",
                password_hash=hash_password("AdminPass123!"),
                full_name="Exam Admin",
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        examiner = db.query(User).filter(User.email == "exam_examiner@osm.local").first()
        if not examiner:
            examiner = User(
                email="exam_examiner@osm.local",
                password_hash=hash_password("ExaminerPass123!"),
                full_name="Exam Examiner",
                role="examiner",
                is_active=True,
            )
            db.add(examiner)
            db.commit()
            db.refresh(examiner)

        admin_token, _ = create_access_token(admin.id, admin.role)
        examiner_token, _ = create_access_token(examiner.id, examiner.role)

        return {
            "admin_token": admin_token,
            "admin_id": admin.id,
            "examiner_token": examiner_token,
            "examiner_id": examiner.id,
        }
    finally:
        db.close()


def test_create_exam_admin(auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['admin_token']}"}
    payload = {
        "title": "Computer Networks Midterm",
        "course_code": "CS-301",
        "exam_date": "2026-10-15",
        "settings": {
            "ocr_low_conf_threshold": 0.85,
        },
    }
    response = client.post("/api/v1/exams", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Computer Networks Midterm"
    assert data["course_code"] == "CS-301"
    assert data["status"] == "draft"
    assert data["settings"]["ocr_low_conf_threshold"] == 0.85
    assert data["settings"]["too_fast_seconds"] == 10  # default merged


def test_create_exam_invalid_settings(auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['admin_token']}"}
    payload = {
        "title": "Invalid Settings Exam",
        "course_code": "CS-999",
        "settings": {
            "ocr_low_conf_threshold": 1.5,  # must be between 0 and 1
        },
    }
    response = client.post("/api/v1/exams", json=payload, headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_SETTINGS"


def test_create_exam_forbidden_for_examiner(auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['examiner_token']}"}
    payload = {
        "title": "Hacker Exam",
        "course_code": "CS-000",
    }
    response = client.post("/api/v1/exams", json=payload, headers=headers)
    assert response.status_code == 403


def test_get_exams_list(auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['admin_token']}"}
    response = client.get("/api/v1/exams", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_exam_detail_counts(auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['admin_token']}"}
    # Create exam
    payload = {"title": "Algorithm Design", "course_code": "CS-401"}
    exam_res = client.post("/api/v1/exams", json=payload, headers=headers).json()
    exam_id = exam_res["id"]

    # Get detail
    response = client.get(f"/api/v1/exams/{exam_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == exam_id
    assert data["question_count"] == 0
    assert data["sheet_count"] == 0
    assert data["answer_count"] == 0


def test_update_exam(auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['admin_token']}"}
    payload = {"title": "OS Final Exam", "course_code": "CS-202"}
    exam = client.post("/api/v1/exams", json=payload, headers=headers).json()

    update_payload = {"title": "Operating Systems Final Exam (Updated)"}
    response = client.patch(f"/api/v1/exams/{exam['id']}", json=update_payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Operating Systems Final Exam (Updated)"


def test_question_lifecycle_and_rubric(auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['admin_token']}"}
    # 1. Create Exam
    exam = client.post(
        "/api/v1/exams",
        json={"title": "Database Systems", "course_code": "CS-501"},
        headers=headers,
    ).json()
    exam_id = exam["id"]

    # 2. Add Question (Q1)
    q_payload = {
        "question_number": "1",
        "text": "Explain ACID properties in relational databases.",
        "max_marks": 10.0,
        "evaluation_mode": "standard",
        "display_order": 1,
    }
    q_res = client.post(f"/api/v1/exams/{exam_id}/questions", json=q_payload, headers=headers)
    assert q_res.status_code == 201
    question = q_res.json()
    question_id = question["id"]
    assert question["question_number"] == "1"
    assert question["max_marks"] == 10.0

    # 3. Duplicate Question Number returns 409
    dup_res = client.post(f"/api/v1/exams/{exam_id}/questions", json=q_payload, headers=headers)
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "DUPLICATE_QUESTION_NUMBER"

    # 4. Rubric sum mismatch (criteria sum 8 != question max_marks 10) (R1)
    bad_rubric_payload = {
        "criteria": [
            {"id": "c1", "name": "Atomicity", "max_marks": 2.5},
            {"id": "c2", "name": "Consistency", "max_marks": 2.5},
            {"id": "c3", "name": "Isolation", "max_marks": 3.0},
        ],
        "guidance": "Mention transaction rollbacks.",
    }
    rubric_err = client.put(f"/api/v1/questions/{question_id}/rubric", json=bad_rubric_payload, headers=headers)
    assert rubric_err.status_code == 422
    assert rubric_err.json()["error"]["code"] == "RUBRIC_SUM_MISMATCH"

    # 5. Rubric duplicate criterion IDs (R1)
    dup_id_payload = {
        "criteria": [
            {"id": "c1", "name": "Atomicity", "max_marks": 5.0},
            {"id": "c1", "name": "Consistency", "max_marks": 5.0},
        ],
    }
    dup_id_res = client.put(f"/api/v1/questions/{question_id}/rubric", json=dup_id_payload, headers=headers)
    assert dup_id_res.status_code == 422
    assert dup_id_res.json()["error"]["code"] == "DUPLICATE_CRITERION_ID"

    # 6. Valid Rubric Save (sum == 10.0)
    valid_rubric = {
        "criteria": [
            {"id": "c1", "name": "Atomicity", "max_marks": 2.5, "description": "All or nothing"},
            {"id": "c2", "name": "Consistency", "max_marks": 2.5, "description": "Valid state transitions"},
            {"id": "c3", "name": "Isolation", "max_marks": 2.5, "description": "Concurrent execution correctness"},
            {"id": "c4", "name": "Durability", "max_marks": 2.5, "description": "Committed updates survive crashes"},
        ],
        "guidance": "Accept equivalent formal definitions.",
    }
    rubric_ok = client.put(f"/api/v1/questions/{question_id}/rubric", json=valid_rubric, headers=headers)
    assert rubric_ok.status_code == 200
    assert len(rubric_ok.json()["criteria"]) == 4

    # 7. Read Rubric (R2)
    get_rubric = client.get(f"/api/v1/questions/{question_id}/rubric", headers=headers)
    assert get_rubric.status_code == 200
    assert get_rubric.json()["question_id"] == question_id

    # 8. List Questions for Exam (Q2)
    q_list = client.get(f"/api/v1/exams/{exam_id}/questions", headers=headers)
    assert q_list.status_code == 200
    assert len(q_list.json()) == 1
    assert q_list.json()[0]["rubric"] is not None

    # 9. Update Question (Q3)
    update_q = client.patch(
        f"/api/v1/questions/{question_id}",
        json={"text": "Explain ACID properties in relational database transactions."},
        headers=headers,
    )
    assert update_q.status_code == 200
    assert "transactions" in update_q.json()["text"]


def test_transition_preconditions_and_failures(auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['admin_token']}"}
    # Create empty draft exam
    exam = client.post(
        "/api/v1/exams",
        json={"title": "Empty Exam For Transition Test", "course_code": "TEST-101"},
        headers=headers,
    ).json()
    exam_id = exam["id"]

    # 1. Invalid transition direct to completed
    inv_res = client.post(
        f"/api/v1/exams/{exam_id}/transition",
        json={"to": "completed"},
        headers=headers,
    )
    assert inv_res.status_code == 409
    assert inv_res.json()["error"]["code"] == "INVALID_TRANSITION"

    # 2. Transition draft -> evaluation without questions & sheets
    trans_res = client.post(
        f"/api/v1/exams/{exam_id}/transition",
        json={"to": "evaluation"},
        headers=headers,
    )
    assert trans_res.status_code == 409
    assert trans_res.json()["error"]["code"] == "PRECONDITION_FAILED"
    failures = trans_res.json()["error"]["details"]["failures"]
    assert any("question is required" in f.lower() for f in failures)
    assert any("answer sheet must be mapped" in f.lower() for f in failures)
