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
from app.models.evaluation import Evaluation

client = TestClient(app)

@pytest.fixture(scope="module")
def analytics_data():
    from app.core.security import create_access_token, hash_password
    db = SessionLocal()

    admin = db.query(User).filter(User.email == "ana_admin@osm.local").first()
    if not admin:
        admin = User(email="ana_admin@osm.local", password_hash=hash_password("pw"), full_name="Ana Admin", role="admin")
        db.add(admin)

    examiner = db.query(User).filter(User.email == "ana_exam@osm.local").first()
    if not examiner:
        examiner = User(email="ana_exam@osm.local", password_hash=hash_password("pw"), full_name="Ana Exam", role="examiner")
        db.add(examiner)

    db.commit()
    db.refresh(admin)
    db.refresh(examiner)

    admin_token, _ = create_access_token(str(admin.id), role="admin")
    examiner_token, _ = create_access_token(str(examiner.id), role="examiner")

    exam = Exam(title="Ana Exam", course_code="ANA101", status="evaluation", created_by=admin.id)
    db.add(exam)
    db.commit()
    db.refresh(exam)

    q1 = Question(exam_id=exam.id, question_number="1", text="Q1", max_marks=10.0, display_order=1)
    db.add(q1)
    db.commit()
    db.refresh(q1)

    student = db.query(Student).filter(Student.roll_number == "ANA_001").first()
    if not student:
        student = Student(roll_number="ANA_001", full_name="Ana Student")
        db.add(student)
        db.commit()
        db.refresh(student)

    sheet = AnswerSheet(exam_id=exam.id, student_id=student.id, anon_code="S_ANA", status="mapped", uploaded_by=admin.id)
    db.add(sheet)
    db.commit()
    db.refresh(sheet)

    ans = Answer(
        exam_id=exam.id, answer_sheet_id=sheet.id, question_id=q1.id, is_attempted=True,
        ocr_status="done", ai_status="done", marking_status="marked",
        final_marks=8.0, final_source="examiner", assigned_examiner_id=examiner.id
    )
    db.add(ans)
    db.commit()
    db.refresh(ans)
    
    eval_row = Evaluation(
        answer_id=ans.id, examiner_id=examiner.id, marks_awarded=8.0,
        source="manual", status="submitted", active_seconds=60
    )
    db.add(eval_row)
    db.commit()
    
    exam_id = exam.id
    db.close()
    
    return {
        "exam_id": exam_id,
        "admin_token": admin_token,
        "examiner_token": examiner_token
    }

def test_analytics_overview(analytics_data):
    headers = {"Authorization": f"Bearer {analytics_data['admin_token']}"}
    res = client.get(f"/api/v1/exams/{analytics_data['exam_id']}/analytics/overview", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["answers_total"] == 1
    assert data["marked"] == 1
    assert data["avg_seconds_per_answer"] == 60.0

def test_analytics_examiners(analytics_data):
    headers = {"Authorization": f"Bearer {analytics_data['admin_token']}"}
    res = client.get(f"/api/v1/exams/{analytics_data['exam_id']}/analytics/examiners", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["examiner"] == "Ana Exam"
    assert data[0]["mean"] == 8.0
    assert data[0]["avg_seconds"] == 60.0
    assert data[0]["pct_manual"] == 100.0

def test_analytics_questions(analytics_data):
    headers = {"Authorization": f"Bearer {analytics_data['admin_token']}"}
    res = client.get(f"/api/v1/exams/{analytics_data['exam_id']}/analytics/questions", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["question_number"] == "1"
    assert data[0]["mean"] == 8.0

def test_my_progress(analytics_data):
    headers = {"Authorization": f"Bearer {analytics_data['examiner_token']}"}
    res = client.get(f"/api/v1/exams/{analytics_data['exam_id']}/analytics/my-progress", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["assigned"] == 1
    assert data["marked"] == 1
    assert data["remaining"] == 0
