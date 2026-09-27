"""
Tests for OCR Pipeline & Workspace Answer Endpoints (O1-O4, N1-N2).
Contract: api-spec.md §8, §9 and architecture.md §8.
"""
import io
import time
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.db import SessionLocal
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.answer import Answer
from app.models.exam import Exam
from app.models.question import Question, Rubric
from app.models.sheet import AnswerSheet, AnswerSheetPage
from app.models.student import Student
from app.models.user import User

client = TestClient(app)


def create_dummy_jpeg() -> bytes:
    img = Image.new("RGB", (100, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def setup_ocr_data():
    db = SessionLocal()
    try:
        # Admin user
        admin = db.query(User).filter(User.email == "ocr_admin@osm.local").first()
        if not admin:
            admin = User(
                email="ocr_admin@osm.local",
                password_hash=hash_password("AdminPass123!"),
                full_name="OCR Admin",
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        # Examiner 1
        examiner1 = db.query(User).filter(User.email == "ocr_ex1@osm.local").first()
        if not examiner1:
            examiner1 = User(
                email="ocr_ex1@osm.local",
                password_hash=hash_password("ExPass123!"),
                full_name="OCR Examiner 1",
                role="examiner",
                is_active=True,
            )
            db.add(examiner1)
            db.commit()
            db.refresh(examiner1)

        # Examiner 2
        examiner2 = db.query(User).filter(User.email == "ocr_ex2@osm.local").first()
        if not examiner2:
            examiner2 = User(
                email="ocr_ex2@osm.local",
                password_hash=hash_password("ExPass123!"),
                full_name="OCR Examiner 2",
                role="examiner",
                is_active=True,
            )
            db.add(examiner2)
            db.commit()
            db.refresh(examiner2)

        # Moderator
        moderator = db.query(User).filter(User.email == "ocr_mod@osm.local").first()
        if not moderator:
            moderator = User(
                email="ocr_mod@osm.local",
                password_hash=hash_password("ModPass123!"),
                full_name="OCR Moderator",
                role="moderator",
                is_active=True,
            )
            db.add(moderator)
            db.commit()
            db.refresh(moderator)

        admin_token, _ = create_access_token(admin.id, admin.role)
        ex1_token, _ = create_access_token(examiner1.id, examiner1.role)
        ex2_token, _ = create_access_token(examiner2.id, examiner2.role)
        mod_token, _ = create_access_token(moderator.id, moderator.role)

        # Create Exam
        exam = Exam(
            title="OCR Test Exam",
            course_code="OCR-101",
            status="draft",
            settings={"ocr": {"min_confidence": 0.80}},
            created_by=admin.id,
        )
        db.add(exam)
        db.commit()
        db.refresh(exam)

        # Create Question
        q1 = Question(
            exam_id=exam.id,
            question_number="1",
            text="Explain TCP 3-way handshake.",
            max_marks=10.0,
            evaluation_mode="standard",
            display_order=1,
        )
        db.add(q1)
        db.commit()
        db.refresh(q1)

        rubric = Rubric(
            question_id=q1.id,
            criteria=[{"id": "c1", "name": "SYN, SYN-ACK, ACK", "max_marks": 10.0}],
            guidance="Standard explanation",
        )
        db.add(rubric)
        db.commit()

        # Create Student
        student = Student(
            roll_number=f"OCR-ROLL-{exam.id}",
            full_name="OCR Candidate",
            department="CSE",
        )
        db.add(student)
        db.commit()
        db.refresh(student)

        # Create AnswerSheet
        sheet = AnswerSheet(
            exam_id=exam.id,
            student_id=student.id,
            anon_code=f"S-OCR-{exam.id}",
            status="uploaded",
            uploaded_by=admin.id,
        )
        db.add(sheet)
        db.commit()
        db.refresh(sheet)

        page1 = AnswerSheetPage(
            answer_sheet_id=sheet.id,
            page_number=1,
            storage_key=f"sheets/{exam.id}/{sheet.id}/page_1.jpg",
            width=800,
            height=1100,
        )
        db.add(page1)
        db.commit()
        db.refresh(page1)

        return {
            "admin_token": admin_token,
            "admin_id": admin.id,
            "ex1_token": ex1_token,
            "ex1_id": examiner1.id,
            "ex2_token": ex2_token,
            "ex2_id": examiner2.id,
            "mod_token": mod_token,
            "exam_id": exam.id,
            "q1_id": q1.id,
            "sheet_id": sheet.id,
            "page1_id": page1.id,
        }
    finally:
        db.close()


def test_batch_ocr_no_mapped_sheets(setup_ocr_data):
    headers = {"Authorization": f"Bearer {setup_ocr_data['admin_token']}"}
    exam_id = setup_ocr_data["exam_id"]

    # O1 without mapped sheets returns 409 NO_MAPPED_SHEETS
    res = client.post(f"/api/v1/exams/{exam_id}/ocr/run", json={}, headers=headers)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "NO_MAPPED_SHEETS"


def test_map_and_trigger_batch_ocr(setup_ocr_data):
    admin_headers = {"Authorization": f"Bearer {setup_ocr_data['admin_token']}"}
    sheet_id = setup_ocr_data["sheet_id"]
    exam_id = setup_ocr_data["exam_id"]
    q1_id = setup_ocr_data["q1_id"]

    # AS4: Map page 1 to question 1
    map_res = client.put(
        f"/api/v1/answer-sheets/{sheet_id}/mapping",
        json={"items": [{"question_id": q1_id, "page_start": 1, "page_end": 1, "is_attempted": True}]},
        headers=admin_headers,
    )
    assert map_res.status_code == 200
    answers = map_res.json()
    assert len(answers) == 1
    answer_id = answers[0]["id"]

    # Assign answer to examiner 1
    assign_res = client.post(
        f"/api/v1/exams/{exam_id}/assignments",
        json={"examiner_ids": [setup_ocr_data["ex1_id"]], "strategy": "by_sheet"},
        headers=admin_headers,
    )
    assert assign_res.status_code == 200

    # O4: Check processing status
    status_res = client.get(
        f"/api/v1/exams/{exam_id}/processing-status",
        headers=admin_headers,
    )
    assert status_res.status_code == 200
    st = status_res.json()
    assert st["ocr"]["pending"] >= 1
    assert "marking" in st

    # O1: Batch OCR run now succeeds with 202
    ocr_res = client.post(
        f"/api/v1/exams/{exam_id}/ocr/run",
        json={"answer_ids": [answer_id]},
        headers=admin_headers,
    )
    assert ocr_res.status_code == 202
    assert ocr_res.json()["queued"] == 1


def test_ocr_single_rerun_and_text_patch(setup_ocr_data):
    admin_headers = {"Authorization": f"Bearer {setup_ocr_data['admin_token']}"}
    ex1_headers = {"Authorization": f"Bearer {setup_ocr_data['ex1_token']}"}
    ex2_headers = {"Authorization": f"Bearer {setup_ocr_data['ex2_token']}"}
    exam_id = setup_ocr_data["exam_id"]

    db = SessionLocal()
    ans = db.query(Answer).filter(Answer.exam_id == exam_id).first()
    answer_id = ans.id
    db.close()

    # O2: Re-run fails if exam is not in 'evaluation' status
    fail_rerun = client.post(f"/api/v1/answers/{answer_id}/ocr", headers=ex1_headers)
    assert fail_rerun.status_code == 409
    assert fail_rerun.json()["error"]["code"] == "ANSWER_LOCKED"

    # Transition exam to evaluation
    trans_res = client.post(
        f"/api/v1/exams/{exam_id}/transition",
        json={"to": "evaluation"},
        headers=admin_headers,
    )
    assert trans_res.status_code == 200

    # Examiner 2 (not assigned) gets 403
    forbidden_rerun = client.post(f"/api/v1/answers/{answer_id}/ocr", headers=ex2_headers)
    assert forbidden_rerun.status_code == 403

    # Examiner 1 succeeds
    ok_rerun = client.post(f"/api/v1/answers/{answer_id}/ocr", headers=ex1_headers)
    assert ok_rerun.status_code == 202
    assert ok_rerun.json()["queued"] == 1

    # O3: Correct OCR text with empty text fails with 422
    empty_patch = client.patch(
        f"/api/v1/answers/{answer_id}/text",
        json={"verified_text": "   ", "ocr_verified": True},
        headers=ex1_headers,
    )
    assert empty_patch.status_code == 422
    assert empty_patch.json()["error"]["code"] == "EMPTY_TEXT"

    # O3: Valid text update by assigned examiner
    patch_res = client.patch(
        f"/api/v1/answers/{answer_id}/text",
        json={
            "verified_text": "TCP uses SYN, SYN-ACK, and ACK to establish connection.",
            "ocr_verified": True,
        },
        headers=ex1_headers,
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["verified"] is True
    assert "TCP uses SYN" in data["verified_text"]


def test_answer_list_and_workspace_detail(setup_ocr_data):
    admin_headers = {"Authorization": f"Bearer {setup_ocr_data['admin_token']}"}
    ex1_headers = {"Authorization": f"Bearer {setup_ocr_data['ex1_token']}"}
    ex2_headers = {"Authorization": f"Bearer {setup_ocr_data['ex2_token']}"}
    exam_id = setup_ocr_data["exam_id"]

    db = SessionLocal()
    ans = db.query(Answer).filter(Answer.exam_id == exam_id).first()
    answer_id = ans.id
    db.close()

    # N1: List answers for examiner 1 (sees 1)
    res_ex1 = client.get(f"/api/v1/answers?exam_id={exam_id}", headers=ex1_headers)
    assert res_ex1.status_code == 200
    assert res_ex1.json()["total"] == 1

    # N1: Examiner 2 (sees 0 assigned)
    res_ex2 = client.get(f"/api/v1/answers?exam_id={exam_id}", headers=ex2_headers)
    assert res_ex2.status_code == 200
    assert res_ex2.json()["total"] == 0

    # N2: Examiner 2 gets 403 trying to access Examiner 1's answer
    forb_res = client.get(f"/api/v1/answers/{answer_id}", headers=ex2_headers)
    assert forb_res.status_code == 403

    # N2: Examiner 1 workspace payload
    ws_res = client.get(f"/api/v1/answers/{answer_id}", headers=ex1_headers)
    assert ws_res.status_code == 200
    ws = ws_res.json()
    assert ws["id"] == answer_id
    assert ws["anon_code"].startswith("S-OCR-")
    assert ws["student"] is None  # BLIND MARKING: hidden from examiner
    assert ws["question"]["question_number"] == "1"
    assert ws["ocr"]["verified"] is True
    assert ws["navigation"]["total"] == 1
    assert ws["navigation"]["position"] == 1

    # N2: Admin workspace payload has student info
    admin_ws = client.get(f"/api/v1/answers/{answer_id}", headers=admin_headers)
    assert admin_ws.status_code == 200
    admin_data = admin_ws.json()
    assert admin_data["student"] is not None
    assert admin_data["student"]["full_name"] == "OCR Candidate"
