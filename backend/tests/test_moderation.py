import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app

client = TestClient(app)
from app.models.exam import Exam
from app.models.student import Student
from app.models.sheet import AnswerSheet
from app.models.answer import Answer
from app.models.question import Question
from app.models.evaluation import Evaluation
from app.models.anomaly import Anomaly
from app.models.user import User
from app.core.db import SessionLocal

@pytest.fixture(scope="module")
def moderation_data():
    from app.core.security import create_access_token, hash_password
    db = SessionLocal()
    
    admin = db.query(User).filter(User.email == "mod_admin@osm.local").first()
    if not admin:
        admin = User(email="mod_admin@osm.local", password_hash=hash_password("pw"), full_name="A", role="admin")
        db.add(admin)
        
    moderator = db.query(User).filter(User.email == "mod_mod@osm.local").first()
    if not moderator:
        moderator = User(email="mod_mod@osm.local", password_hash=hash_password("pw"), full_name="M", role="moderator")
        db.add(moderator)
        
    examiner = db.query(User).filter(User.email == "mod_exam@osm.local").first()
    if not examiner:
        examiner = User(email="mod_exam@osm.local", password_hash=hash_password("pw"), full_name="E", role="examiner")
        db.add(examiner)
        
    db.commit()
    db.refresh(admin)
    db.refresh(moderator)
    db.refresh(examiner)
    
    admin_token, _ = create_access_token(str(admin.id), role="admin")
    moderator_token, _ = create_access_token(str(moderator.id), role="moderator")
    
    exam = Exam(title="Mod Exam", course_code="MOD101", status="moderation", created_by=admin.id)
    db.add(exam)
    db.commit()
    db.refresh(exam)
    
    q1 = Question(exam_id=exam.id, question_number="1", text="Q1", max_marks=10.0, display_order=1)
    db.add(q1)
    db.commit()
    db.refresh(q1)
    
    student = db.query(Student).filter(Student.roll_number == "MOD_001").first()
    if not student:
        student = Student(roll_number="MOD_001", full_name="Mod Student")
        db.add(student)
        db.commit()
        db.refresh(student)
    
    sheet = AnswerSheet(exam_id=exam.id, student_id=student.id, anon_code="S_MOD", status="mapped", uploaded_by=admin.id)
    db.add(sheet)
    db.commit()
    db.refresh(sheet)
    
    ans = Answer(
        exam_id=exam.id, answer_sheet_id=sheet.id, question_id=q1.id, is_attempted=True,
        ocr_status="done", ai_status="done", marking_status="flagged",
        final_marks=5.0, final_source="examiner", assigned_examiner_id=examiner.id
    )
    db.add(ans)
    db.commit()
    db.refresh(ans)
    
    eval_row = Evaluation(
        answer_id=ans.id, examiner_id=examiner.id, marks_awarded=5.0,
        source="manual", status="submitted"
    )
    db.add(eval_row)
    db.commit()
    
    an1 = Anomaly(
        exam_id=exam.id, type="MISSING_MARKS", severity="high",
        answer_id=ans.id, question_id=q1.id, examiner_id=examiner.id,
        score=0.9, details={}, status="open", dedupe_key=f"MISSING_MARKS_{ans.id}"
    )
    db.add(an1)
    db.commit()
    
    exam_id = exam.id
    ans_id = ans.id
    
    db.close()
    
    return {
        "exam_id": exam_id,
        "answer_id": ans_id,
        "moderator_token": moderator_token,
        "admin_token": admin_token
    }

def test_moderation_queue(moderation_data):
    mod_headers = {"Authorization": f"Bearer {moderation_data['moderator_token']}"}
    res = client.get(f"/api/v1/exams/{moderation_data['exam_id']}/moderation/queue", headers=mod_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["answer_id"] == moderation_data["answer_id"]
    assert data["items"][0]["anomalies"][0]["type"] == "MISSING_MARKS"
    assert data["items"][0]["anomalies"][0]["severity"] == "high"

def test_moderate_answer_override(moderation_data):
    mod_headers = {"Authorization": f"Bearer {moderation_data['moderator_token']}"}
    payload = {
        "decision": "overridden",
        "moderated_marks": 7.5,
        "reason": "Examiner was too strict"
    }
    res = client.post(f"/api/v1/answers/{moderation_data['answer_id']}/moderation", json=payload, headers=mod_headers)
    assert res.status_code == 200
    
    db = SessionLocal()
    ans = db.get(Answer, moderation_data["answer_id"])
    assert ans.final_marks == 7.5
    assert ans.final_source == "moderator"
    assert ans.marking_status == "moderated"
    
    # Check anomalies are resolved
    anomalies = db.scalars(select(Anomaly).where(Anomaly.answer_id == moderation_data["answer_id"])).all()
    for a in anomalies:
        assert a.status == "resolved"
    db.close()

def test_moderate_answer_confirm_invalid(moderation_data):
    mod_headers = {"Authorization": f"Bearer {moderation_data['moderator_token']}"}
    # Original marks are 5.0, confirming with 6.0 should fail validation
    payload = {
        "decision": "confirmed",
        "moderated_marks": 6.0
    }
    res = client.post(f"/api/v1/answers/{moderation_data['answer_id']}/moderation", json=payload, headers=mod_headers)
    assert res.status_code == 422
