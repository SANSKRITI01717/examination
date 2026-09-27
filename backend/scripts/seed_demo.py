import sys
from pathlib import Path
import random
import uuid

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.exam import Exam
from app.models.student import Student
from app.models.sheet import AnswerSheet
from app.models.question import Question
from app.models.answer import Answer
from app.models.evaluation import AIEvaluation, Evaluation
from app.models.anomaly import Anomaly

def create_demo_data():
    db = SessionLocal()
    
    # Check if demo exam already exists
    if db.query(Exam).filter(Exam.course_code == "DEMO104").first():
        print("Demo data already exists.")
        db.close()
        return

    print("Creating Demo Users...")
    admin = db.query(User).filter(User.email == "demo_admin@osm.local").first()
    if not admin:
        admin = User(email="demo_admin@osm.local", password_hash=hash_password("pw"), full_name="Demo Admin", role="admin")
        db.add(admin)
        
    examiner = db.query(User).filter(User.email == "demo_exam@osm.local").first()
    if not examiner:
        examiner = User(email="demo_exam@osm.local", password_hash=hash_password("pw"), full_name="Demo Examiner", role="examiner")
        db.add(examiner)
        
    moderator = db.query(User).filter(User.email == "demo_mod@osm.local").first()
    if not moderator:
        moderator = User(email="demo_mod@osm.local", password_hash=hash_password("pw"), full_name="Demo Moderator", role="moderator")
        db.add(moderator)
        
    db.commit()
    db.refresh(admin)
    db.refresh(examiner)
    db.refresh(moderator)

    print("Creating Demo Exam...")
    exam = Exam(title="Computer Science 104 Midterm", course_code="DEMO104", status="evaluation", created_by=admin.id)
    db.add(exam)
    db.commit()
    db.refresh(exam)
    
    print("Creating Questions...")
    q1 = Question(exam_id=exam.id, question_number="1a", text="Explain Polymorphism", max_marks=5.0, display_order=1)
    q2 = Question(exam_id=exam.id, question_number="1b", text="What is Inheritance?", max_marks=5.0, display_order=2)
    q3 = Question(exam_id=exam.id, question_number="2", text="Write a sorting function in Python", max_marks=10.0, display_order=3)
    db.add_all([q1, q2, q3])
    db.commit()
    
    questions = [q1, q2, q3]
    
    print("Creating Students & Answer Sheets...")
    for i in range(1, 16):
        student = Student(roll_number=f"DEMO104_ST_{i:03d}", full_name=f"Demo Student {i}")
        db.add(student)
        db.commit()
        db.refresh(student)
        
        sheet = AnswerSheet(
            exam_id=exam.id, student_id=student.id, anon_code=f"ANON_104_{i:03d}",
            status="mapped", uploaded_by=admin.id
        )
        db.add(sheet)
        db.commit()
        db.refresh(sheet)
        
        from app.models.sheet import AnswerSheetPage
        page1 = AnswerSheetPage(answer_sheet_id=sheet.id, page_number=1, storage_key=f"sheets/demo/sheet_{i}_p1.jpg")
        page2 = AnswerSheetPage(answer_sheet_id=sheet.id, page_number=2, storage_key=f"sheets/demo/sheet_{i}_p2.jpg")
        db.add_all([page1, page2])
        db.commit()
        
        # Create answers for this sheet
        for q in questions:
            # Simulate marking progression
            rand_val = random.random()
            if rand_val < 0.2:
                marking_status = "pending"
                final_source = None
                final_marks = None
            elif rand_val < 0.7:
                marking_status = "marked"
                final_source = "examiner"
                final_marks = min(float(q.max_marks), round(random.uniform(0, float(q.max_marks)), 1))
            elif rand_val < 0.9:
                marking_status = "flagged"
                final_source = "examiner"
                final_marks = min(float(q.max_marks), round(random.uniform(0, float(q.max_marks)), 1))
            else:
                marking_status = "moderated"
                final_source = "moderator"
                final_marks = min(float(q.max_marks), round(random.uniform(0, float(q.max_marks)), 1))
                
            ans = Answer(
                exam_id=exam.id, answer_sheet_id=sheet.id, question_id=q.id, is_attempted=True,
                ocr_status="done", ai_status="done", marking_status=marking_status,
                final_marks=final_marks, final_source=final_source, assigned_examiner_id=examiner.id,
                ocr_text=f"Student answer for {q.text}..."
            )
            db.add(ans)
            db.commit()
            db.refresh(ans)
            
            # AI evaluation
            ai_marks = min(float(q.max_marks), round(random.uniform(0, float(q.max_marks)), 1))
            ai_eval = AIEvaluation(
                answer_id=ans.id, mode_requested="standard", mode_used="standard",
                model_name="demo-model", prompt_version="v1", input_hash="demo_hash",
                suggested_marks=ai_marks, max_marks=q.max_marks, confidence=random.uniform(0.6, 0.95),
                criteria=[], overall_reason="AI found it somewhat correct"
            )
            db.add(ai_eval)
            
            # Human evaluation if marked
            if marking_status != "pending":
                eval_row = Evaluation(
                    answer_id=ans.id, examiner_id=examiner.id, marks_awarded=final_marks,
                    source="manual" if random.random() > 0.5 else "ai_accepted", status="submitted",
                    active_seconds=random.randint(20, 120)
                )
                db.add(eval_row)
                
            # If flagged, create anomaly
            if marking_status in ["flagged", "moderated"]:
                an = Anomaly(
                    exam_id=exam.id, type="AI_DISAGREEMENT", severity="high" if random.random() > 0.5 else "medium",
                    answer_id=ans.id, question_id=q.id, examiner_id=examiner.id,
                    score=1.0, details={"diff": abs(ai_marks - float(final_marks)) if final_marks else 0},
                    status="open" if marking_status == "flagged" else "resolved",
                    dedupe_key=f"{exam.id}_{ans.id}_AI_DISAGREEMENT"
                )
                db.add(an)
                
        db.commit()

    print("Demo Data Creation Complete!")
    db.close()

if __name__ == "__main__":
    create_demo_data()
