"""
Tests for Reference Documents (D1, D2, D3, D5) and reference-grounded evaluation.
Contract: api-spec.md §11 and ai-pipeline.md §6.

Uses FakeEmbeddingProvider / FakeVectorStore — no real OpenAI/Pinecone calls.
"""
import io
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.ai.llm.base import LLMResult
from app.ai.rag.base import EmbeddingResult, RagError, RetrievedChunk
from app.core.db import SessionLocal
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.answer import Answer
from app.models.exam import Exam
from app.models.question import Question, Rubric
from app.models.reference import ReferenceDocument
from app.models.sheet import AnswerSheet, AnswerSheetPage
from app.models.student import Student
from app.models.user import User

client = TestClient(app)

GOOD_LLM_RESPONSE = json.dumps(
    {
        "criteria": [{"criterion_id": "c1", "awarded_marks": 4, "reason": "Matches the reference material."}],
        "overall_reason": "Correct per the uploaded reference.",
        "confidence": 0.9,
    }
)


class FakeEmbeddingProvider:
    def embed(self, text: str) -> EmbeddingResult:
        return EmbeddingResult(vector=[0.1, 0.2, 0.3], model_name="fake-embed")


class FakeFailingEmbeddingProvider:
    def embed(self, text: str) -> EmbeddingResult:
        raise RagError("embedding provider unreachable (fake)")


class FakeVectorStore:
    """Records upserts; query() returns whatever `matches` was set to."""

    def __init__(self, matches=None):
        self.matches = matches if matches is not None else []
        self.upserted = []
        self.deleted_docs = []

    def upsert(self, namespace, records):
        self.upserted.extend(records)

    def query(self, namespace, vector, top_k, question_id_filter=None):
        return self.matches[:top_k]

    def delete_by_doc(self, namespace, doc_id):
        self.deleted_docs.append(doc_id)


class FakeLLMClient:
    def __init__(self, responses):
        self._responses = list(responses)

    def generate_json(self, system_prompt, user_prompt):
        raw = self._responses.pop(0) if self._responses else GOOD_LLM_RESPONSE
        return LLMResult(raw_text=raw, latency_ms=5, model_name="fake-model")


def _run_job_synchronously(fn, *args, **kwargs):
    fn(*args, **kwargs)


@pytest.fixture(scope="module")
def setup_ref_data():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "ref_admin@osm.local").first()
        if not admin:
            admin = User(
                email="ref_admin@osm.local",
                password_hash=hash_password("AdminPass123!"),
                full_name="Ref Admin",
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        ex1 = db.query(User).filter(User.email == "ref_ex1@osm.local").first()
        if not ex1:
            ex1 = User(
                email="ref_ex1@osm.local",
                password_hash=hash_password("ExPass123!"),
                full_name="Ref Examiner",
                role="examiner",
                is_active=True,
            )
            db.add(ex1)
            db.commit()
            db.refresh(ex1)

        admin_token, _ = create_access_token(admin.id, admin.role)
        ex1_token, _ = create_access_token(ex1.id, ex1.role)

        exam = Exam(
            title="RAG Test Exam",
            course_code="RAG-101",
            status="draft",
            settings={"retrieval_top_k": 4, "retrieval_min_score": 0.50},
            created_by=admin.id,
        )
        db.add(exam)
        db.commit()
        db.refresh(exam)

        q1 = Question(
            exam_id=exam.id,
            question_number="1",
            text="What is the capital of the fictional country of Wakanda?",
            max_marks=4.0,
            evaluation_mode="reference_grounded",
            display_order=1,
        )
        db.add(q1)
        db.commit()
        db.refresh(q1)

        rubric = Rubric(
            question_id=q1.id,
            criteria=[{"id": "c1", "name": "Correct answer", "max_marks": 4.0, "description": "Names the capital"}],
            guidance=None,
        )
        db.add(rubric)
        db.commit()

        return {
            "admin_token": admin_token,
            "ex1_token": ex1_token,
            "ex1_id": ex1.id,
            "exam_id": exam.id,
            "q1_id": q1.id,
        }
    finally:
        db.close()


def test_upload_unsupported_file_type(setup_ref_data):
    admin_headers = {"Authorization": f"Bearer {setup_ref_data['admin_token']}"}
    res = client.post(
        f"/api/v1/exams/{setup_ref_data['exam_id']}/reference-documents",
        data={"title": "Bad File", "doc_type": "guideline"},
        files={"file": ("notes.exe", io.BytesIO(b"binary junk"), "application/octet-stream")},
        headers=admin_headers,
    )
    assert res.status_code == 415
    assert res.json()["error"]["code"] == "UNSUPPORTED_FILE"


def test_upload_and_index_txt_document(setup_ref_data):
    admin_headers = {"Authorization": f"Bearer {setup_ref_data['admin_token']}"}
    fake_embed = FakeEmbeddingProvider()
    fake_store = FakeVectorStore()

    with patch("app.services.reference_service.submit_job", side_effect=_run_job_synchronously), \
         patch("app.services.reference_service.get_embedding_provider", return_value=fake_embed), \
         patch("app.services.reference_service.get_vector_store", return_value=fake_store):
        res = client.post(
            f"/api/v1/exams/{setup_ref_data['exam_id']}/reference-documents",
            data={"title": "Wakanda Facts", "doc_type": "official_answer", "question_id": str(setup_ref_data["q1_id"])},
            files={"file": ("facts.txt", io.BytesIO(b"The capital of Wakanda is Birnin Zana."), "text/plain")},
            headers=admin_headers,
        )

    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "uploaded"

    setup_ref_data["doc_id"] = body["id"]

    # D2: list shows it and status is indexed because job ran synchronously
    list_res = client.get(f"/api/v1/exams/{setup_ref_data['exam_id']}/reference-documents", headers=admin_headers)
    assert list_res.status_code == 200
    docs = list_res.json()
    doc_in_list = next(d for d in docs if d["id"] == body["id"])
    assert doc_in_list["status"] == "indexed"
    assert doc_in_list["chunk_count"] == 1
    assert len(fake_store.upserted) == 1
    assert fake_store.upserted[0].metadata["text"] == "The capital of Wakanda is Birnin Zana."


def test_upload_indexing_failure_when_embedding_unavailable(setup_ref_data):
    admin_headers = {"Authorization": f"Bearer {setup_ref_data['admin_token']}"}
    fake_store = FakeVectorStore()

    with patch("app.services.reference_service.submit_job", side_effect=_run_job_synchronously), \
         patch("app.services.reference_service.get_embedding_provider", return_value=FakeFailingEmbeddingProvider()), \
         patch("app.services.reference_service.get_vector_store", return_value=fake_store):
        res = client.post(
            f"/api/v1/exams/{setup_ref_data['exam_id']}/reference-documents",
            data={"title": "Will Fail", "doc_type": "guideline"},
            files={"file": ("fail.txt", io.BytesIO(b"some content that will fail to embed"), "text/plain")},
            headers=admin_headers,
        )

    assert res.status_code == 201  # upload itself succeeds; indexing fails in the background
    doc_id = res.json()["id"]

    db = SessionLocal()
    doc = db.get(ReferenceDocument, doc_id)
    assert doc.status == "failed"
    assert doc.error is not None
    db.close()


def test_reference_search_no_indexed_documents():
    admin_token, _ = create_access_token(1, "admin")  # any admin; exam has no docs at all
    db = SessionLocal()
    exam = Exam(title="Empty Ref Exam", course_code="EMPTY-1", status="draft", settings={}, created_by=1)
    db.add(exam)
    db.commit()
    db.refresh(exam)
    exam_id = exam.id
    db.close()

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.post(
        f"/api/v1/exams/{exam_id}/reference-search",
        json={"query": "anything", "top_k": 4},
        headers=admin_headers,
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "NO_INDEXED_DOCUMENTS"


def test_reference_search_success(setup_ref_data):
    admin_headers = {"Authorization": f"Bearer {setup_ref_data['admin_token']}"}
    fake_store = FakeVectorStore(
        matches=[RetrievedChunk(doc_id=setup_ref_data["doc_id"], chunk_index=0, score=0.91, text="Birnin Zana is the capital.")]
    )
    with patch("app.services.reference_service.get_embedding_provider", return_value=FakeEmbeddingProvider()), \
         patch("app.services.reference_service.get_vector_store", return_value=fake_store):
        res = client.post(
            f"/api/v1/exams/{setup_ref_data['exam_id']}/reference-search",
            json={"query": "capital of Wakanda", "top_k": 4},
            headers=admin_headers,
        )
    assert res.status_code == 200
    chunks = res.json()["chunks"]
    assert len(chunks) == 1
    assert chunks[0]["title"] == "Wakanda Facts"


def test_evaluation_uses_reference_grounded_mode_when_chunks_found(setup_ref_data):
    db = SessionLocal()
    student = Student(roll_number=f"RAG-ROLL-{setup_ref_data['exam_id']}", full_name="RAG Candidate")
    db.add(student)
    db.commit()
    db.refresh(student)

    sheet = AnswerSheet(
        exam_id=setup_ref_data["exam_id"], student_id=student.id, anon_code=f"S-RAG-{setup_ref_data['exam_id']}",
        status="uploaded", uploaded_by=1,
    )
    db.add(sheet)
    db.commit()
    db.refresh(sheet)
    db.add(AnswerSheetPage(answer_sheet_id=sheet.id, page_number=1, storage_key="x", width=1, height=1))
    db.commit()
    sheet_id = sheet.id
    db.close()

    admin_headers = {"Authorization": f"Bearer {setup_ref_data['admin_token']}"}
    map_res = client.put(
        f"/api/v1/answer-sheets/{sheet_id}/mapping",
        json={"items": [{"question_id": setup_ref_data["q1_id"], "page_start": 1, "page_end": 1, "is_attempted": True}]},
        headers=admin_headers,
    )
    answer_id = map_res.json()[0]["id"]

    client.post(
        f"/api/v1/exams/{setup_ref_data['exam_id']}/assignments",
        json={"examiner_ids": [setup_ref_data["ex1_id"]], "strategy": "by_sheet"},
        headers=admin_headers,
    )
    client.post(f"/api/v1/exams/{setup_ref_data['exam_id']}/transition", json={"to": "evaluation"}, headers=admin_headers)

    db = SessionLocal()
    ans = db.get(Answer, answer_id)
    ans.ocr_text = "The capital is Birnin Zana."
    ans.ocr_status = "done"
    ans.ocr_confidence = 0.95
    db.commit()
    db.close()

    ex1_headers = {"Authorization": f"Bearer {setup_ref_data['ex1_token']}"}
    fake_store = FakeVectorStore(
        matches=[RetrievedChunk(doc_id=setup_ref_data["doc_id"], chunk_index=0, score=0.9, text="Birnin Zana is the capital.", title="Wakanda Facts")]
    )
    fake_llm = FakeLLMClient([GOOD_LLM_RESPONSE])

    with patch("app.ai.rag.retriever.get_embedding_provider", return_value=FakeEmbeddingProvider()), \
         patch("app.ai.rag.retriever.get_vector_store", return_value=fake_store), \
         patch("app.services.evaluator_service.get_llm_client", return_value=fake_llm):
        res = client.post(f"/api/v1/answers/{answer_id}/ai-evaluation", json={}, headers=ex1_headers)

    assert res.status_code == 200
    body = res.json()
    assert body["mode_requested"] == "reference_grounded"
    assert body["mode_used"] == "reference_grounded"
    assert "REFERENCE_UNAVAILABLE" not in body["warnings"]
    assert "NO_REFERENCE_FOUND" not in body["warnings"]
    assert body["retrieval"] is not None
    assert body["retrieval"][0]["doc_id"] == setup_ref_data["doc_id"]

    setup_ref_data["rag_answer_id"] = answer_id


def test_evaluation_falls_back_when_no_chunks_score_high_enough(setup_ref_data):
    answer_id = setup_ref_data["rag_answer_id"]
    ex1_headers = {"Authorization": f"Bearer {setup_ref_data['ex1_token']}"}

    fake_store = FakeVectorStore(matches=[])  # nothing found
    fake_llm = FakeLLMClient([GOOD_LLM_RESPONSE])

    with patch("app.ai.rag.retriever.get_embedding_provider", return_value=FakeEmbeddingProvider()), \
         patch("app.ai.rag.retriever.get_vector_store", return_value=fake_store), \
         patch("app.services.evaluator_service.get_llm_client", return_value=fake_llm):
        res = client.post(f"/api/v1/answers/{answer_id}/ai-evaluation", json={}, headers=ex1_headers)

    assert res.status_code == 200
    body = res.json()
    assert body["mode_used"] == "standard"
    assert "NO_REFERENCE_FOUND" in body["warnings"]


def test_evaluation_falls_back_when_vector_store_unavailable(setup_ref_data):
    answer_id = setup_ref_data["rag_answer_id"]
    ex1_headers = {"Authorization": f"Bearer {setup_ref_data['ex1_token']}"}
    fake_llm = FakeLLMClient([GOOD_LLM_RESPONSE])

    with patch("app.ai.rag.retriever.get_embedding_provider", return_value=FakeFailingEmbeddingProvider()), \
         patch("app.services.evaluator_service.get_llm_client", return_value=fake_llm):
        res = client.post(f"/api/v1/answers/{answer_id}/ai-evaluation", json={}, headers=ex1_headers)

    assert res.status_code == 200
    body = res.json()
    assert body["mode_used"] == "standard"
    assert "REFERENCE_UNAVAILABLE" in body["warnings"]


def test_standard_mode_question_never_calls_vector_store(setup_ref_data):
    """Regression guard: a standard question must not touch retrieval at all."""
    db = SessionLocal()
    q2 = Question(
        exam_id=setup_ref_data["exam_id"], question_number="2", text="A plain standard question.",
        max_marks=2.0, evaluation_mode="standard", display_order=2,
    )
    db.add(q2)
    db.commit()
    db.refresh(q2)
    db.add(Rubric(question_id=q2.id, criteria=[{"id": "c1", "name": "Only criterion", "max_marks": 2.0}]))
    db.commit()

    student = Student(roll_number=f"STD-ROLL-{setup_ref_data['exam_id']}", full_name="Standard Candidate")
    db.add(student)
    db.commit()
    db.refresh(student)
    sheet = AnswerSheet(
        exam_id=setup_ref_data["exam_id"], student_id=student.id, anon_code=f"S-STD-{setup_ref_data['exam_id']}",
        status="uploaded", uploaded_by=1,
    )
    db.add(sheet)
    db.commit()
    db.refresh(sheet)
    db.add(AnswerSheetPage(answer_sheet_id=sheet.id, page_number=1, storage_key="x", width=1, height=1))
    db.commit()
    q2_id, sheet_id = q2.id, sheet.id
    db.close()

    admin_headers = {"Authorization": f"Bearer {setup_ref_data['admin_token']}"}
    map_res = client.put(
        f"/api/v1/answer-sheets/{sheet_id}/mapping",
        json={"items": [{"question_id": q2_id, "page_start": 1, "page_end": 1, "is_attempted": True}]},
        headers=admin_headers,
    )
    answer_id = map_res.json()[0]["id"]
    client.post(
        f"/api/v1/exams/{setup_ref_data['exam_id']}/assignments",
        json={"examiner_ids": [setup_ref_data["ex1_id"]], "strategy": "by_sheet"},
        headers=admin_headers,
    )

    db = SessionLocal()
    ans = db.get(Answer, answer_id)
    ans.ocr_text = "A plain answer."
    ans.ocr_status = "done"
    db.commit()
    db.close()

    ex1_headers = {"Authorization": f"Bearer {setup_ref_data['ex1_token']}"}
    fake_llm = FakeLLMClient([json.dumps({
        "criteria": [{"criterion_id": "c1", "awarded_marks": 2, "reason": "Fine."}],
        "overall_reason": "ok", "confidence": 0.8,
    })])

    # Deliberately do NOT patch app.ai.rag.retriever — if the standard path
    # ever calls it, this will try a real network call and fail loudly.
    with patch("app.services.evaluator_service.get_llm_client", return_value=fake_llm):
        res = client.post(f"/api/v1/answers/{answer_id}/ai-evaluation", json={}, headers=ex1_headers)

    assert res.status_code == 200
    assert res.json()["mode_used"] == "standard"
    assert res.json()["retrieval"] is None


def test_delete_reference_document(setup_ref_data):
    db = SessionLocal()
    exam = db.get(Exam, setup_ref_data["exam_id"])
    exam.status = "draft"
    db.commit()
    db.close()

    admin_headers = {"Authorization": f"Bearer {setup_ref_data['admin_token']}"}
    fake_store = FakeVectorStore()

    with patch("app.services.reference_service.submit_job", side_effect=_run_job_synchronously), \
         patch("app.services.reference_service.get_embedding_provider", return_value=FakeEmbeddingProvider()), \
         patch("app.services.reference_service.get_vector_store", return_value=fake_store):
        upload_res = client.post(
            f"/api/v1/exams/{setup_ref_data['exam_id']}/reference-documents",
            data={"title": "Temp Doc", "doc_type": "other"},
            files={"file": ("temp.txt", io.BytesIO(b"delete me"), "text/plain")},
            headers=admin_headers,
        )
    doc_id = upload_res.json()["id"]

    with patch("app.services.reference_service.get_vector_store", return_value=fake_store):
        del_res = client.delete(f"/api/v1/reference-documents/{doc_id}", headers=admin_headers)

    assert del_res.status_code == 204
    assert doc_id in fake_store.deleted_docs

    db = SessionLocal()
    assert db.get(ReferenceDocument, doc_id) is None
    db.close()
