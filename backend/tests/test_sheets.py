"""
Tests for Students, Answer Sheets, Page Mapping & Assignments (S1-S2, AS1-AS6).
"""
import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.db import SessionLocal
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.exam import Exam
from app.models.question import Question, Rubric
from app.models.user import User

client = TestClient(app)


def create_dummy_jpeg() -> bytes:
    img = Image.new("RGB", (200, 200), color="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def setup_data():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "sheet_admin@osm.local").first()
        if not admin:
            admin = User(
                email="sheet_admin@osm.local",
                password_hash=hash_password("AdminPass123!"),
                full_name="Sheet Admin",
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        examiner = db.query(User).filter(User.email == "sheet_examiner@osm.local").first()
        if not examiner:
            examiner = User(
                email="sheet_examiner@osm.local",
                password_hash=hash_password("ExaminerPass123!"),
                full_name="Sheet Examiner",
                role="examiner",
                is_active=True,
            )
            db.add(examiner)
            db.commit()
            db.refresh(examiner)

        admin_token, _ = create_access_token(admin.id, admin.role)
        examiner_token, _ = create_access_token(examiner.id, examiner.role)

        # Setup exam + question
        exam = Exam(
            title="Sheet Test Exam",
            course_code="ST-101",
            status="draft",
            settings={},
            created_by=admin.id,
        )
        db.add(exam)
        db.commit()
        db.refresh(exam)

        q1 = Question(
            exam_id=exam.id,
            question_number="1",
            text="Explain OSI model layers.",
            max_marks=10.0,
            evaluation_mode="standard",
            display_order=1,
        )
        db.add(q1)
        db.commit()
        db.refresh(q1)

        rubric = Rubric(
            question_id=q1.id,
            criteria=[{"id": "c1", "name": "Layers", "max_marks": 10.0}],
        )
        db.add(rubric)
        db.commit()

        return {
            "admin_token": admin_token,
            "admin_id": admin.id,
            "examiner_token": examiner_token,
            "examiner_id": examiner.id,
            "exam_id": exam.id,
            "q1_id": q1.id,
        }
    finally:
        db.close()


def test_student_endpoints(setup_data):
    headers = {"Authorization": f"Bearer {setup_data['admin_token']}"}
    roll_no = f"CS2026-{setup_data['exam_id']}-01"

    # S1: Create student
    res = client.post(
        "/api/v1/students",
        json={"roll_number": roll_no, "full_name": "Alice Candidate", "department": "CSE"},
        headers=headers,
    )
    assert res.status_code == 201
    student = res.json()
    assert student["roll_number"] == roll_no
    student_id = student["id"]

    # Duplicate roll number returns 409
    dup = client.post(
        "/api/v1/students",
        json={"roll_number": roll_no, "full_name": "Alice Duplicate"},
        headers=headers,
    )
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "ROLL_EXISTS"

    # S2: Search students
    search_res = client.get(f"/api/v1/students?q={roll_no}", headers=headers)
    assert search_res.status_code == 200
    assert search_res.json()["total"] >= 1


def test_answer_sheet_upload_and_mapping_flow(setup_data):
    headers = {"Authorization": f"Bearer {setup_data['admin_token']}"}
    exam_id = setup_data["exam_id"]

    # Create candidate
    student_res = client.post(
        "/api/v1/students",
        json={"roll_number": f"ROLL-SHEET-{exam_id}", "full_name": "Bob Student"},
        headers=headers,
    ).json()
    student_id = student_res["id"]

    # AS1: Upload Answer Sheet with 2 pages
    img1 = create_dummy_jpeg()
    img2 = create_dummy_jpeg()

    files = [
        ("files", ("page_1.jpg", img1, "image/jpeg")),
        ("files", ("page_2.jpg", img2, "image/jpeg")),
    ]
    data = {"student_id": str(student_id)}

    upload_res = client.post(
        f"/api/v1/exams/{exam_id}/answer-sheets",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {setup_data['admin_token']}"},
    )
    assert upload_res.status_code == 201
    sheet = upload_res.json()
    sheet_id = sheet["id"]
    assert sheet["status"] == "uploaded"
    assert sheet["anon_code"].startswith("S-")

    # Duplicate upload for same student returns 409
    dup_res = client.post(
        f"/api/v1/exams/{exam_id}/answer-sheets",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {setup_data['admin_token']}"},
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "SHEET_EXISTS"

    # AS2: List answer sheets
    list_res = client.get(f"/api/v1/exams/{exam_id}/answer-sheets", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # AS3: Get answer sheet detail
    detail_res = client.get(f"/api/v1/answer-sheets/{sheet_id}", headers=headers)
    assert detail_res.status_code == 200
    sheet_detail = detail_res.json()
    assert sheet_detail["page_count"] == 2
    assert len(sheet_detail["pages"]) == 2

    # AS5: Stream page image
    first_page_id = sheet_detail["pages"][0]["id"]
    page_img_res = client.get(f"/api/v1/pages/{first_page_id}/image", headers=headers)
    assert page_img_res.status_code == 200
    assert page_img_res.headers["content-type"] == "image/jpeg"
    assert len(page_img_res.content) > 0

    # AS4: Map page ranges
    # Invalid page range returns 422
    bad_map = client.put(
        f"/api/v1/answer-sheets/{sheet_id}/mapping",
        json={"items": [{"question_id": setup_data["q1_id"], "page_start": 1, "page_end": 5}]},
        headers=headers,
    )
    assert bad_map.status_code == 422
    assert bad_map.json()["error"]["code"] == "PAGE_RANGE_INVALID"

    # Valid mapping
    map_res = client.put(
        f"/api/v1/answer-sheets/{sheet_id}/mapping",
        json={"items": [{"question_id": setup_data["q1_id"], "page_start": 1, "page_end": 2, "is_attempted": True}]},
        headers=headers,
    )
    assert map_res.status_code == 200
    answers = map_res.json()
    assert len(answers) == 1
    assert answers[0]["is_attempted"] is True

    # AS6: Assignment to examiner
    assign_res = client.post(
        f"/api/v1/exams/{exam_id}/assignments",
        json={"examiner_ids": [setup_data["examiner_id"]], "strategy": "by_sheet"},
        headers=headers,
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["assigned"] >= 1
    assert str(setup_data["examiner_id"]) in assign_res.json()["per_examiner"]
