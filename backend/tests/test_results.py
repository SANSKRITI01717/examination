import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient
from app.main import app
from app.core.db import SessionLocal
from app.models.user import User
from app.models.exam import Exam
from app.models.student import Student
from app.models.sheet import AnswerSheet
from app.models.question import Question
from app.models.answer import Answer
from app.models.result import Result

client = TestClient(app)

@pytest.fixture(scope="module")
def result_data():
    from app.core.security import create_access_token, hash_password
    db = SessionLocal()

    admin = db.query(User).filter(User.email == "res_admin@osm.local").first()
    if not admin:
        admin = User(email="res_admin@osm.local", password_hash=hash_password("pw"), full_name="Res Admin", role="admin")
        db.add(admin)

    db.commit()
    db.refresh(admin)
    admin_token, _ = create_access_token(str(admin.id), role="admin")

    exam = Exam(title="Res Exam", course_code="RES101", status="moderation", created_by=admin.id)
    db.add(exam)
    db.commit()
    db.refresh(exam)

    q1 = Question(exam_id=exam.id, question_number="1", text="Q1", max_marks=10.0, display_order=1)
    db.add(q1)
    db.commit()
    db.refresh(q1)

    student = db.query(Student).filter(Student.roll_number == "RES_001").first()
    if not student:
        student = Student(roll_number="RES_001", full_name="Res Student")
        db.add(student)
        db.commit()
        db.refresh(student)

    sheet = AnswerSheet(exam_id=exam.id, student_id=student.id, anon_code="S_RES", status="mapped", uploaded_by=admin.id)
    db.add(sheet)
    db.commit()
    db.refresh(sheet)

    ans = Answer(
        exam_id=exam.id, answer_sheet_id=sheet.id, question_id=q1.id, is_attempted=True,
        ocr_status="done", ai_status="done", marking_status="marked",
        final_marks=7.5, final_source="examiner"
    )
    db.add(ans)
    db.commit()
    
    exam_id = exam.id
    db.close()
    
    return {
        "exam_id": exam_id,
        "admin_token": admin_token
    }

def test_compute_results(result_data):
    headers = {"Authorization": f"Bearer {result_data['admin_token']}"}
    res = client.post(f"/api/v1/exams/{result_data['exam_id']}/results/compute", headers=headers)
    assert res.status_code == 200
    assert res.json()["computed"] == 1

def test_list_results(result_data):
    headers = {"Authorization": f"Bearer {result_data['admin_token']}"}
    res = client.get(f"/api/v1/exams/{result_data['exam_id']}/results", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["total_marks"] == 7.5
    assert data["items"][0]["percentage"] == 75.0
    assert data["stats"]["mean"] == 7.5

def test_get_result_detail(result_data):
    # First get the result id
    db = SessionLocal()
    r = db.scalars(select(Result).where(Result.exam_id == result_data["exam_id"])).first()
    rid = r.id
    db.close()
    
    headers = {"Authorization": f"Bearer {result_data['admin_token']}"}
    res = client.get(f"/api/v1/results/{rid}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["result"]["total_marks"] == 7.5
    assert len(data["breakdown"]) == 1
    assert data["breakdown"][0]["marks"] == 7.5

def test_publish_results(result_data):
    headers = {"Authorization": f"Bearer {result_data['admin_token']}"}
    res = client.post(f"/api/v1/exams/{result_data['exam_id']}/results/publish", headers=headers)
    assert res.status_code == 200
    assert res.json()["published"] is True
    
    # Check exam status
    db = SessionLocal()
    e = db.get(Exam, result_data["exam_id"])
    assert e.status == "completed"
    db.close()
