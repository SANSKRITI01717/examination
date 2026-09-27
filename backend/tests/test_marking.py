"""
Tests for examiner marking endpoints (M1, M2) and their guards.
Contract: api-spec.md §12; invariants 2, 3, 5, 7, 8 in database-schema.md §6.

Uses a FakeLLMClient so no real LLM is ever called. Each test creates its own answer,
so tests do not depend on each other's state.
"""
import json
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.ai.llm.base import LLMResult
from app.core.db import SessionLocal
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.anomaly import Anomaly
from app.models.answer import Answer
from app.models.evaluation import AIEvaluation, Evaluation
from app.models.exam import Exam
from app.models.question import Question, Rubric
from app.models.sheet import AnswerSheet
from app.models.student import Student
from app.models.user import User

client = TestClient(app)

# Rubric: c1 (max 5) + c2 (max 3) = question max 8. AI awards 4 + 3 = 7.
AI_RESPONSE = json.dumps(
    {
        "criteria": [
            {"criterion_id": "c1", "awarded_marks": 4, "reason": "Mostly correct handshake steps."},
            {"criterion_id": "c2", "awarded_marks": 3, "reason": "Purpose explained well."},
        ],
        "overall_reason": "Good answer, one step slightly vague.",
        "confidence": 0.9,
    }
)


class FakeLLMClient:
    def generate_json(self, system_prompt: str, user_prompt: str) -> LLMResult:
        return LLMResult(raw_text=AI_RESPONSE, latency_ms=5, model_name="fake-model")


def _get_or_create_user(db, email, role, name):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            password_hash=hash_password("Passw0rd!123"),
            full_name=name,
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _headers(user):
    token, _ = create_access_token(user.id, user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def ctx():
    db = SessionLocal()
    try:
        admin = _get_or_create_user(db, "mark_admin@osm.local", "admin", "Mark Admin")
        ex1 = _get_or_create_user(db, "mark_ex1@osm.local", "examiner", "Mark Examiner 1")
        ex2 = _get_or_create_user(db, "mark_ex2@osm.local", "examiner", "Mark Examiner 2")
        mod = _get_or_create_user(db, "mark_mod@osm.local", "moderator", "Mark Moderator")

        exam = Exam(
            title="Marking Test Exam",
            course_code="MARK-101",
            status="evaluation",
            settings={"ai_low_conf_threshold": 0.70},
            created_by=admin.id,
        )
        db.add(exam)
        db.commit()
        db.refresh(exam)

        q = Question(
            exam_id=exam.id,
            question_number="1",
            text="Explain the TCP three-way handshake.",
            max_marks=8.0,
            evaluation_mode="standard",
            display_order=1,
        )
        db.add(q)
        db.commit()
        db.refresh(q)
        db.add(
            Rubric(
                question_id=q.id,
                criteria=[
                    {"id": "c1", "name": "Steps", "max_marks": 5.0, "description": "SYN, SYN-ACK, ACK"},
                    {"id": "c2", "name": "Purpose", "max_marks": 3.0, "description": "Why it exists"},
                ],
                guidance="Accept alternative wording.",
            )
        )
        db.commit()

        return {
            "exam_id": exam.id,
            "q_id": q.id,
            "admin": _headers(admin),
            "ex1": _headers(ex1),
            "ex1_id": ex1.id,
            "ex2": _headers(ex2),
            "mod": _headers(mod),
        }
    finally:
        db.close()


def _make_answer(ctx, *, review_required=False, verified=False, assigned=True):
    """Creates an isolated sheet + answer assigned to examiner 1, with OCR text present."""
    db = SessionLocal()
    try:
        suffix = uuid.uuid4().hex[:10]
        student = Student(roll_number=f"MARK-{suffix}", full_name="Mark Candidate", department="CSE")
        db.add(student)
        db.commit()
        db.refresh(student)

        sheet = AnswerSheet(
            exam_id=ctx["exam_id"],
            student_id=student.id,
            anon_code=f"S-MARK-{suffix}",
            status="mapped",
            uploaded_by=db.query(User).filter(User.email == "mark_admin@osm.local").first().id,
        )
        db.add(sheet)
        db.commit()
        db.refresh(sheet)

        ans = Answer(
            exam_id=ctx["exam_id"],
            answer_sheet_id=sheet.id,
            question_id=ctx["q_id"],
            is_attempted=True,
            ocr_status="done",
            ocr_text="Client sends SYN, server replies SYN-ACK, client sends ACK.",
            ocr_confidence=0.95,
            ocr_review_required=review_required,
            ocr_verified=verified,
            assigned_examiner_id=ctx["ex1_id"] if assigned else None,
        )
        db.add(ans)
        db.commit()
        db.refresh(ans)
        return ans.id
    finally:
        db.close()


def _run_ai(ctx, answer_id):
    """Real V1 call with the fake LLM -> real AIEvaluation row with a real input_hash."""
    with patch("app.services.evaluator_service.get_llm_client", return_value=FakeLLMClient()):
        res = client.post(f"/api/v1/answers/{answer_id}/ai-evaluation", json={}, headers=ctx["ex1"])
    assert res.status_code == 200, res.text
    return res.json()["id"]


def _accept(ctx, answer_id, ai_id, headers=None):
    return client.post(
        f"/api/v1/answers/{answer_id}/evaluation/accept-ai",
        json={"ai_evaluation_id": ai_id, "active_seconds": 45},
        headers=headers or ctx["ex1"],
    )


def _put(ctx, answer_id, headers=None, **overrides):
    body = {"marks_awarded": 6, "source": "manual", "active_seconds": 30, "submit": True}
    body.update(overrides)
    return client.put(
        f"/api/v1/answers/{answer_id}/evaluation", json=body, headers=headers or ctx["ex1"]
    )


def _answer_row(answer_id):
    db = SessionLocal()
    try:
        a = db.get(Answer, answer_id)
        return {
            "final_marks": float(a.final_marks) if a.final_marks is not None else None,
            "final_source": a.final_source,
            "marking_status": a.marking_status,
        }
    finally:
        db.close()


# ---------------------------------------------------------------- M1: accept-ai


def test_accept_ai_success_writes_final_marks(ctx):
    answer_id = _make_answer(ctx)
    ai_id = _run_ai(ctx, answer_id)

    # Rule 1: running the AI alone must never touch final marks.
    assert _answer_row(answer_id) == {"final_marks": None, "final_source": None, "marking_status": "pending"}

    # N2 creates a placeholder draft evaluation on first open; M1 must reuse it.
    assert client.get(f"/api/v1/answers/{answer_id}", headers=ctx["ex1"]).status_code == 200

    res = _accept(ctx, answer_id, ai_id)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["marks_awarded"] == 7.0
    assert body["source"] == "ai_accepted"
    assert body["status"] == "submitted"
    assert body["submitted_at"] is not None
    assert body["examiner"]["full_name"] == "Mark Examiner 1"
    assert body["criterion_marks"] == [
        {"criterion_id": "c1", "awarded_marks": 4.0},
        {"criterion_id": "c2", "awarded_marks": 3.0},
    ]

    assert _answer_row(answer_id) == {
        "final_marks": 7.0,
        "final_source": "examiner",
        "marking_status": "marked",
    }

    db = SessionLocal()
    try:
        evs = db.query(Evaluation).filter(Evaluation.answer_id == answer_id).all()
        assert len(evs) == 1  # placeholder reused, not duplicated
        assert evs[0].ai_evaluation_id == ai_id
        assert evs[0].active_seconds == 45
        assert evs[0].opened_at is not None  # preserved from N2
        # AI record is untouched (invariant 4)
        assert db.query(AIEvaluation).filter(AIEvaluation.answer_id == answer_id).count() == 1
    finally:
        db.close()

    # N2 now shows the submitted evaluation and the final marks.
    ws = client.get(f"/api/v1/answers/{answer_id}", headers=ctx["ex1"]).json()
    assert ws["final_marks"] == 7.0
    assert ws["evaluation"]["source"] == "ai_accepted"


def test_accept_ai_blocked_when_ocr_not_verified(ctx):
    answer_id = _make_answer(ctx, review_required=True, verified=False)
    ai_id = _run_ai(ctx, answer_id)

    res = _accept(ctx, answer_id, ai_id)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "OCR_NOT_VERIFIED"
    assert _answer_row(answer_id)["final_marks"] is None

    db = SessionLocal()
    try:
        assert db.query(Evaluation).filter(
            Evaluation.answer_id == answer_id, Evaluation.status == "submitted"
        ).count() == 0
    finally:
        db.close()


def test_modified_and_manual_marks_allowed_when_ocr_not_verified(ctx):
    """Invariant 8: only accept-ai is refused; the examiner can still mark by hand."""
    answer_id = _make_answer(ctx, review_required=True, verified=False)
    ai_id = _run_ai(ctx, answer_id)

    res = _put(ctx, answer_id, marks_awarded=5, source="ai_modified", ai_evaluation_id=ai_id)
    assert res.status_code == 200, res.text
    assert _answer_row(answer_id)["final_marks"] == 5.0

    answer2 = _make_answer(ctx, review_required=True, verified=False)
    assert _put(ctx, answer2, marks_awarded=4.5).status_code == 200
    assert _answer_row(answer2)["final_marks"] == 4.5


def test_accept_ai_blocked_when_stale_then_recovers_after_rerun(ctx):
    answer_id = _make_answer(ctx)
    old_ai_id = _run_ai(ctx, answer_id)

    # Examiner corrects the text -> the earlier suggestion no longer matches (invariant 7).
    patch_res = client.patch(
        f"/api/v1/answers/{answer_id}/text",
        json={"verified_text": "Corrected: client SYN, server SYN-ACK, client ACK.", "ocr_verified": True},
        headers=ctx["ex1"],
    )
    assert patch_res.status_code == 200

    res = _accept(ctx, answer_id, old_ai_id)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "AI_EVAL_STALE"
    assert _answer_row(answer_id)["final_marks"] is None

    # Re-running AI on the corrected text produces a fresh, acceptable suggestion.
    new_ai_id = _run_ai(ctx, answer_id)
    assert new_ai_id != old_ai_id
    assert _accept(ctx, answer_id, new_ai_id).status_code == 200
    assert _answer_row(answer_id)["final_marks"] == 7.0


def test_accept_ai_rejects_unknown_or_foreign_ai_evaluation(ctx):
    answer_a = _make_answer(ctx)
    answer_b = _make_answer(ctx)
    ai_of_b = _run_ai(ctx, answer_b)

    assert _accept(ctx, answer_a, ai_of_b).status_code == 404  # belongs to another answer
    assert _accept(ctx, answer_a, 999999999).status_code == 404
    assert _answer_row(answer_a)["final_marks"] is None


# ------------------------------------------------------------ M2: save / submit


def test_manual_submit_sets_final_marks(ctx):
    answer_id = _make_answer(ctx)
    res = _put(ctx, answer_id, marks_awarded=6.5, comment="Solid but incomplete.")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["marks_awarded"] == 6.5
    assert body["source"] == "manual"
    assert body["status"] == "submitted"
    assert body["comment"] == "Solid but incomplete."
    assert _answer_row(answer_id) == {
        "final_marks": 6.5,
        "final_source": "examiner",
        "marking_status": "marked",
    }


def test_resubmission_updates_final_marks(ctx):
    answer_id = _make_answer(ctx)
    assert _put(ctx, answer_id, marks_awarded=3).status_code == 200
    assert _put(ctx, answer_id, marks_awarded=6).status_code == 200
    assert _answer_row(answer_id)["final_marks"] == 6.0
    db = SessionLocal()
    try:
        assert db.query(Evaluation).filter(Evaluation.answer_id == answer_id).count() == 1
    finally:
        db.close()


def test_draft_save_does_not_write_final_marks(ctx):
    answer_id = _make_answer(ctx)
    res = _put(ctx, answer_id, marks_awarded=4, submit=False, comment="wip")
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "draft"
    assert res.json()["submitted_at"] is None
    assert _answer_row(answer_id) == {"final_marks": None, "final_source": None, "marking_status": "pending"}

    # A draft can be edited again, then submitted.
    assert _put(ctx, answer_id, marks_awarded=5, submit=False).status_code == 200
    assert _put(ctx, answer_id, marks_awarded=5, submit=True).status_code == 200
    assert _answer_row(answer_id)["final_marks"] == 5.0

    # After submission, a draft save would desync evaluation and final_marks -> refused.
    res = _put(ctx, answer_id, marks_awarded=2, submit=False)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "ANSWER_LOCKED"
    assert _answer_row(answer_id)["final_marks"] == 5.0


def test_marks_out_of_range_rejected(ctx):
    answer_id = _make_answer(ctx)
    for bad in (8.5, 9, -1, -0.5):
        res = _put(ctx, answer_id, marks_awarded=bad)
        assert res.status_code == 422, bad
        assert res.json()["error"]["code"] == "MARKS_OUT_OF_RANGE"
    # Boundaries are fine.
    assert _put(ctx, answer_id, marks_awarded=0).status_code == 200
    assert _put(ctx, answer_id, marks_awarded=8).status_code == 200
    assert _answer_row(answer_id)["final_marks"] == 8.0


def test_marks_must_be_half_steps(ctx):
    answer_id = _make_answer(ctx)
    res = _put(ctx, answer_id, marks_awarded=3.3)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert _answer_row(answer_id)["final_marks"] is None


def test_criterion_marks_sum_must_match(ctx):
    answer_id = _make_answer(ctx)

    res = _put(
        ctx,
        answer_id,
        marks_awarded=6,
        criterion_marks=[
            {"criterion_id": "c1", "awarded_marks": 3},
            {"criterion_id": "c2", "awarded_marks": 2},
        ],
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "CRITERIA_SUM_MISMATCH"
    assert _answer_row(answer_id)["final_marks"] is None

    ok = _put(
        ctx,
        answer_id,
        marks_awarded=5.5,
        criterion_marks=[
            {"criterion_id": "c1", "awarded_marks": 3.5},
            {"criterion_id": "c2", "awarded_marks": 2},
        ],
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["criterion_marks"] == [
        {"criterion_id": "c1", "awarded_marks": 3.5},
        {"criterion_id": "c2", "awarded_marks": 2.0},
    ]
    assert _answer_row(answer_id)["final_marks"] == 5.5


def test_criterion_marks_individual_validation(ctx):
    answer_id = _make_answer(ctx)

    # c2's max is 3, so 4 is out of range for that criterion even though the sum matches.
    res = _put(
        ctx,
        answer_id,
        marks_awarded=7,
        criterion_marks=[
            {"criterion_id": "c1", "awarded_marks": 3},
            {"criterion_id": "c2", "awarded_marks": 4},
        ],
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "MARKS_OUT_OF_RANGE"

    unknown = _put(
        ctx, answer_id, marks_awarded=2, criterion_marks=[{"criterion_id": "zzz", "awarded_marks": 2}]
    )
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "VALIDATION_ERROR"

    dup = _put(
        ctx,
        answer_id,
        marks_awarded=4,
        criterion_marks=[
            {"criterion_id": "c1", "awarded_marks": 2},
            {"criterion_id": "c1", "awarded_marks": 2},
        ],
    )
    assert dup.status_code == 422
    assert dup.json()["error"]["code"] == "VALIDATION_ERROR"
    assert _answer_row(answer_id)["final_marks"] is None


def test_ai_modified_requires_ai_evaluation_id(ctx):
    answer_id = _make_answer(ctx)

    res = _put(ctx, answer_id, marks_awarded=5, source="ai_modified")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert _answer_row(answer_id)["final_marks"] is None

    ai_id = _run_ai(ctx, answer_id)
    ok = _put(ctx, answer_id, marks_awarded=5, source="ai_modified", ai_evaluation_id=ai_id)
    assert ok.status_code == 200, ok.text
    assert ok.json()["source"] == "ai_modified"
    db = SessionLocal()
    try:
        assert db.query(Evaluation).filter(Evaluation.answer_id == answer_id).one().ai_evaluation_id == ai_id
    finally:
        db.close()


def test_ai_accepted_source_not_allowed_via_put(ctx):
    """ai_accepted exists only through M1, so AI marks can't be smuggled in through M2."""
    answer_id = _make_answer(ctx)
    res = _put(ctx, answer_id, source="ai_accepted")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert _answer_row(answer_id)["final_marks"] is None


def test_missing_required_fields_rejected(ctx):
    answer_id = _make_answer(ctx)
    res = client.put(
        f"/api/v1/answers/{answer_id}/evaluation",
        json={"marks_awarded": 4, "source": "manual"},  # no active_seconds / submit
        headers=ctx["ex1"],
    )
    assert res.status_code == 422
    res = client.post(
        f"/api/v1/answers/{answer_id}/evaluation/accept-ai",
        json={"ai_evaluation_id": 1},  # no active_seconds
        headers=ctx["ex1"],
    )
    assert res.status_code == 422


# ------------------------------------------------------ ownership / lock guards


def test_only_the_assigned_examiner_can_mark(ctx):
    answer_id = _make_answer(ctx)
    ai_id = _run_ai(ctx, answer_id)

    for who in ("ex2", "admin", "mod"):
        assert _put(ctx, answer_id, headers=ctx[who]).status_code == 403, who
        assert _accept(ctx, answer_id, ai_id, headers=ctx[who]).status_code == 403, who

    no_auth = client.put(
        f"/api/v1/answers/{answer_id}/evaluation",
        json={"marks_awarded": 1, "source": "manual", "active_seconds": 1, "submit": True},
    )
    assert no_auth.status_code == 401
    assert _answer_row(answer_id)["final_marks"] is None

    unassigned = _make_answer(ctx, assigned=False)
    assert _put(ctx, unassigned).status_code == 403


def test_unknown_answer_returns_404(ctx):
    assert _put(ctx, 999999999).status_code == 404


def test_marking_locked_when_exam_not_in_evaluation(ctx):
    answer_id = _make_answer(ctx)
    ai_id = _run_ai(ctx, answer_id)

    db = SessionLocal()
    try:
        db.get(Exam, ctx["exam_id"]).status = "moderation"
        db.commit()
    finally:
        db.close()
    try:
        res = _put(ctx, answer_id)
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "ANSWER_LOCKED"
        res = _accept(ctx, answer_id, ai_id)
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "ANSWER_LOCKED"
    finally:
        db = SessionLocal()
        try:
            db.get(Exam, ctx["exam_id"]).status = "evaluation"
            db.commit()
        finally:
            db.close()
    assert _answer_row(answer_id)["final_marks"] is None


def test_moderated_answer_is_locked_for_examiner(ctx):
    answer_id = _make_answer(ctx)
    db = SessionLocal()
    try:
        db.get(Answer, answer_id).marking_status = "moderated"
        db.commit()
    finally:
        db.close()

    res = _put(ctx, answer_id)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "ANSWER_LOCKED"
    assert _answer_row(answer_id)["final_marks"] is None


def test_submit_keeps_flagged_status_when_open_anomaly_exists(ctx):
    answer_id = _make_answer(ctx)
    db = SessionLocal()
    try:
        db.add(
            Anomaly(
                exam_id=ctx["exam_id"],
                type="AI_DISAGREEMENT",
                severity="medium",
                answer_id=answer_id,
                details={},
                status="open",
                dedupe_key=f"AI_DISAGREEMENT:answer:{answer_id}",
            )
        )
        db.get(Answer, answer_id).marking_status = "flagged"
        db.commit()
    finally:
        db.close()

    assert _put(ctx, answer_id, marks_awarded=4).status_code == 200
    assert _answer_row(answer_id) == {
        "final_marks": 4.0,
        "final_source": "examiner",
        "marking_status": "flagged",
    }
