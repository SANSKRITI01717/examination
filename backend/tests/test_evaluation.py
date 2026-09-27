"""
Tests for AI Evaluation endpoints (V1, V3).
Contract: api-spec.md §10 and ai-pipeline.md §4-§9.

Uses a FakeLLMClient (backend-plan.md §8) so tests never call a real LLM provider.
"""
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.ai.llm.base import LLMResult
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

GOOD_RESPONSE = json.dumps(
    {
        "criteria": [
            {"criterion_id": "c1", "awarded_marks": 8, "reason": "Covers SYN, SYN-ACK and ACK correctly."},
        ],
        "overall_reason": "Complete and correct explanation of the handshake.",
        "confidence": 0.9,
    }
)

INVALID_RESPONSE = "Sorry, I cannot help with that request."


class FakeLLMClient:
    """Returns a scripted sequence of raw responses, one per call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def generate_json(self, system_prompt: str, user_prompt: str) -> LLMResult:
        self.calls += 1
        raw = self._responses.pop(0) if self._responses else GOOD_RESPONSE
        return LLMResult(raw_text=raw, latency_ms=10, model_name="fake-model")


@pytest.fixture(scope="module")
def setup_eval_data():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "eval_admin@osm.local").first()
        if not admin:
            admin = User(
                email="eval_admin@osm.local",
                password_hash=hash_password("AdminPass123!"),
                full_name="Eval Admin",
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        ex1 = db.query(User).filter(User.email == "eval_ex1@osm.local").first()
        if not ex1:
            ex1 = User(
                email="eval_ex1@osm.local",
                password_hash=hash_password("ExPass123!"),
                full_name="Eval Examiner 1",
                role="examiner",
                is_active=True,
            )
            db.add(ex1)
            db.commit()
            db.refresh(ex1)

        ex2 = db.query(User).filter(User.email == "eval_ex2@osm.local").first()
        if not ex2:
            ex2 = User(
                email="eval_ex2@osm.local",
                password_hash=hash_password("ExPass123!"),
                full_name="Eval Examiner 2",
                role="examiner",
                is_active=True,
            )
            db.add(ex2)
            db.commit()
            db.refresh(ex2)

        admin_token, _ = create_access_token(admin.id, admin.role)
        ex1_token, _ = create_access_token(ex1.id, ex1.role)
        ex2_token, _ = create_access_token(ex2.id, ex2.role)

        exam = Exam(
            title="Eval Test Exam",
            course_code="EVAL-101",
            status="draft",
            settings={"ai_low_conf_threshold": 0.70},
            created_by=admin.id,
        )
        db.add(exam)
        db.commit()
        db.refresh(exam)

        q1 = Question(
            exam_id=exam.id,
            question_number="1",
            text="Explain the TCP three-way handshake.",
            max_marks=8.0,
            evaluation_mode="standard",
            display_order=1,
        )
        db.add(q1)
        db.commit()
        db.refresh(q1)

        rubric = Rubric(
            question_id=q1.id,
            criteria=[{"id": "c1", "name": "Handshake steps", "max_marks": 8.0, "description": "SYN, SYN-ACK, ACK"}],
            guidance="Accept alternative wording.",
        )
        db.add(rubric)
        db.commit()

        student = Student(
            roll_number=f"EVAL-ROLL-{exam.id}",
            full_name="Eval Candidate",
            department="CSE",
        )
        db.add(student)
        db.commit()
        db.refresh(student)

        sheet = AnswerSheet(
            exam_id=exam.id,
            student_id=student.id,
            anon_code=f"S-EVAL-{exam.id}",
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

        return {
            "admin_token": admin_token,
            "ex1_token": ex1_token,
            "ex1_id": ex1.id,
            "ex2_token": ex2_token,
            "exam_id": exam.id,
            "q1_id": q1.id,
            "sheet_id": sheet.id,
        }
    finally:
        db.close()


def _map_and_assign_and_transition(data):
    admin_headers = {"Authorization": f"Bearer {data['admin_token']}"}

    map_res = client.put(
        f"/api/v1/answer-sheets/{data['sheet_id']}/mapping",
        json={"items": [{"question_id": data["q1_id"], "page_start": 1, "page_end": 1, "is_attempted": True}]},
        headers=admin_headers,
    )
    assert map_res.status_code == 200
    answer_id = map_res.json()[0]["id"]

    assign_res = client.post(
        f"/api/v1/exams/{data['exam_id']}/assignments",
        json={"examiner_ids": [data["ex1_id"]], "strategy": "by_sheet"},
        headers=admin_headers,
    )
    assert assign_res.status_code == 200

    trans_res = client.post(
        f"/api/v1/exams/{data['exam_id']}/transition",
        json={"to": "evaluation"},
        headers=admin_headers,
    )
    assert trans_res.status_code == 200

    return answer_id


def test_ai_evaluation_no_text_yet(setup_eval_data):
    answer_id = _map_and_assign_and_transition(setup_eval_data)
    ex1_headers = {"Authorization": f"Bearer {setup_eval_data['ex1_token']}"}

    res = client.post(f"/api/v1/answers/{answer_id}/ai-evaluation", json={}, headers=ex1_headers)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "NO_TEXT_TO_EVALUATE"


def test_ai_evaluation_forbidden_for_unassigned_examiner(setup_eval_data):
    db = SessionLocal()
    ans = db.query(Answer).filter(Answer.exam_id == setup_eval_data["exam_id"]).first()
    answer_id = ans.id
    db.close()

    ex2_headers = {"Authorization": f"Bearer {setup_eval_data['ex2_token']}"}
    res = client.post(f"/api/v1/answers/{answer_id}/ai-evaluation", json={}, headers=ex2_headers)
    assert res.status_code == 403


def test_ai_evaluation_success_with_fake_llm(setup_eval_data):
    db = SessionLocal()
    ans = db.query(Answer).filter(Answer.exam_id == setup_eval_data["exam_id"]).first()
    ans.ocr_text = "The client sends a SYN packet, the server replies SYN-ACK, then the client sends ACK."
    ans.ocr_status = "done"
    ans.ocr_confidence = 0.95
    db.commit()
    answer_id = ans.id
    db.close()

    ex1_headers = {"Authorization": f"Bearer {setup_eval_data['ex1_token']}"}
    fake = FakeLLMClient([GOOD_RESPONSE])

    with patch("app.services.evaluator_service.get_llm_client", return_value=fake):
        res = client.post(f"/api/v1/answers/{answer_id}/ai-evaluation", json={}, headers=ex1_headers)

    assert res.status_code == 200
    body = res.json()
    assert body["suggested_marks"] == 8.0
    assert body["max_marks"] == 8.0
    assert body["mode_used"] == "standard"
    assert body["stale"] is False
    assert len(body["criteria"]) == 1
    assert body["criteria"][0]["criterion_id"] == "c1"

    # V3: history shows the same suggestion, not stale yet
    hist_res = client.get(f"/api/v1/answers/{answer_id}/ai-evaluations", headers=ex1_headers)
    assert hist_res.status_code == 200
    items = hist_res.json()["items"]
    assert len(items) == 1
    assert items[0]["stale"] is False


def test_ai_evaluation_becomes_stale_after_text_edit(setup_eval_data):
    db = SessionLocal()
    ans = db.query(Answer).filter(Answer.exam_id == setup_eval_data["exam_id"]).first()
    answer_id = ans.id
    db.close()

    ex1_headers = {"Authorization": f"Bearer {setup_eval_data['ex1_token']}"}

    # Examiner corrects the OCR text (O3) — this changes the effective text.
    patch_res = client.patch(
        f"/api/v1/answers/{answer_id}/text",
        json={"verified_text": "Corrected: client SYN, server SYN-ACK, client ACK.", "ocr_verified": True},
        headers=ex1_headers,
    )
    assert patch_res.status_code == 200

    hist_res = client.get(f"/api/v1/answers/{answer_id}/ai-evaluations", headers=ex1_headers)
    assert hist_res.status_code == 200
    items = hist_res.json()["items"]
    assert items[0]["stale"] is True

    # The N2 workspace payload should also report the suggestion as stale.
    ws_res = client.get(f"/api/v1/answers/{answer_id}", headers=ex1_headers)
    assert ws_res.status_code == 200
    assert ws_res.json()["ai"]["latest"]["stale"] is True


def test_ai_evaluation_invalid_output_after_repair_retry_fails(setup_eval_data):
    db = SessionLocal()
    ans = db.query(Answer).filter(Answer.exam_id == setup_eval_data["exam_id"]).first()
    ans.ai_status = "not_requested"
    db.commit()
    answer_id = ans.id
    db.close()

    ex1_headers = {"Authorization": f"Bearer {setup_eval_data['ex1_token']}"}
    # Both the first attempt and the repair retry return invalid output.
    fake = FakeLLMClient([INVALID_RESPONSE, INVALID_RESPONSE])

    with patch("app.services.evaluator_service.get_llm_client", return_value=fake):
        res = client.post(f"/api/v1/answers/{answer_id}/ai-evaluation", json={}, headers=ex1_headers)

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "AI_OUTPUT_INVALID"
    assert fake.calls == 2  # confirms exactly one repair retry happened


def test_ai_evaluation_reference_grounded_falls_back_to_standard(setup_eval_data):
    """A reference_grounded question must still evaluate (Pinecone not built yet — Phase 6)."""
    db = SessionLocal()
    q = db.query(Question).filter(Question.id == setup_eval_data["q1_id"]).first()
    q.evaluation_mode = "reference_grounded"
    db.commit()
    ans = db.query(Answer).filter(Answer.exam_id == setup_eval_data["exam_id"]).first()
    answer_id = ans.id
    db.close()

    ex1_headers = {"Authorization": f"Bearer {setup_eval_data['ex1_token']}"}
    fake = FakeLLMClient([GOOD_RESPONSE])

    with patch("app.services.evaluator_service.get_llm_client", return_value=fake):
        res = client.post(f"/api/v1/answers/{answer_id}/ai-evaluation", json={}, headers=ex1_headers)

    assert res.status_code == 200
    body = res.json()
    assert body["mode_requested"] == "reference_grounded"
    assert body["mode_used"] == "standard"
    assert "REFERENCE_UNAVAILABLE" in body["warnings"]

    # Reset for isolation from any later tests.
    db = SessionLocal()
    q = db.query(Question).filter(Question.id == setup_eval_data["q1_id"]).first()
    q.evaluation_mode = "standard"
    db.commit()
    db.close()
