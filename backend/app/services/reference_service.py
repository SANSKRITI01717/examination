"""
Reference Document Service — D1, D2, D3, D5.
Contract: api-spec.md §11 and ai-pipeline.md §6.

D4 (reindex) is SHOULD HAVE and is not built in this step.
Only reference material is ever indexed — student answers never touch
Pinecone (invariant 11 / database-schema.md §5).
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.rag import get_embedding_provider, get_vector_store
from app.ai.rag.base import RagError, VectorRecord
from app.ai.rag.extractor import extract_text, guess_mime_type
from app.ai.rag.retriever import build_query_text, retrieve_chunks
from app.ai.rag.splitter import chunk_text
from app.core.db import SessionLocal
from app.core.errors import AppError
from app.core.storage import get_storage
from app.core.storage.base import StorageService
from app.models.exam import Exam
from app.models.question import Question
from app.models.reference import ReferenceDocument
from app.services.job_runner import submit_job


def _serialize_doc(doc: ReferenceDocument) -> Dict[str, Any]:
    return {
        "id": doc.id,
        "exam_id": doc.exam_id,
        "question_id": doc.question_id,
        "title": doc.title,
        "doc_type": doc.doc_type,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "error": doc.error,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


def _assert_exam_editable(exam: Optional[Exam]) -> None:
    """
    Same rule as question management (question_service.py): reference material
    is set up while the exam is still in draft, before the evaluation ->
    moderation lifecycle locks question/rubric configuration. This mirrors
    the existing EXAM_LOCKED convention rather than inventing a new one.
    """
    if not exam:
        raise AppError(code="NOT_FOUND", message="Exam not found", status_code=404)
    if exam.status != "draft":
        raise AppError(
            code="EXAM_LOCKED",
            message="Reference documents can only be managed while the exam is in draft",
            status_code=409,
        )


def process_reference_document(doc_id: int) -> None:
    """Background job: extract -> chunk -> embed -> upsert (ai-pipeline.md §6)."""
    db = SessionLocal()
    try:
        doc = db.get(ReferenceDocument, doc_id)
        if not doc:
            return

        doc.status = "indexing"
        db.commit()

        storage = get_storage()
        content = storage.get(doc.storage_key)
        text = extract_text(content, doc.mime_type)
        chunks = chunk_text(text)

        if not chunks:
            doc.status = "failed"
            doc.error = "No extractable text found in the document"
            db.commit()
            return

        embedding_provider = get_embedding_provider()
        vector_store = get_vector_store()
        namespace = f"exam-{doc.exam_id}"
        question_id_for_metadata = doc.question_id if doc.question_id is not None else 0

        records: List[VectorRecord] = []
        for idx, chunk in enumerate(chunks):
            embedding = embedding_provider.embed(chunk)
            records.append(
                VectorRecord(
                    vector_id=f"{doc.id}:{idx}",
                    values=embedding.vector,
                    metadata={
                        "exam_id": doc.exam_id,
                        "doc_id": doc.id,
                        "question_id": question_id_for_metadata,
                        "doc_type": doc.doc_type,
                        "chunk_index": idx,
                        "text": chunk,
                    },
                )
            )

        vector_store.upsert(namespace, records)

        doc.status = "indexed"
        doc.chunk_count = len(chunks)
        doc.pinecone_namespace = namespace
        doc.error = None
        db.commit()
    except RagError as exc:
        doc = db.get(ReferenceDocument, doc_id)
        if doc:
            doc.status = "failed"
            doc.error = f"Embedding/vector store error: {exc}"
            db.commit()
    except AppError as exc:
        doc = db.get(ReferenceDocument, doc_id)
        if doc:
            doc.status = "failed"
            doc.error = exc.message
            db.commit()
    except Exception as exc:
        doc = db.get(ReferenceDocument, doc_id)
        if doc:
            doc.status = "failed"
            doc.error = str(exc)
            db.commit()
    finally:
        db.close()


async def upload_reference_document(
    db: Session,
    exam_id: int,
    title: str,
    doc_type: str,
    file,
    user_id: int,
    question_id: Optional[int],
    storage: StorageService,
) -> Dict[str, Any]:
    exam = db.get(Exam, exam_id)
    _assert_exam_editable(exam)

    if question_id is not None:
        question = db.get(Question, question_id)
        if not question or question.exam_id != exam_id:
            raise AppError(code="NOT_FOUND", message="Question not found in this exam", status_code=404)

    from app.core.config import settings

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise AppError(
            code="FILE_TOO_LARGE",
            message=f"File exceeds maximum size of {settings.MAX_UPLOAD_MB}MB",
            status_code=413,
        )

    filename = file.filename or "document"
    mime_type = guess_mime_type(filename)  # raises 415 UNSUPPORTED_FILE if not pdf/docx/txt
    ext = filename.lower().rsplit(".", 1)[-1]

    doc = ReferenceDocument(
        exam_id=exam_id,
        question_id=question_id,
        title=title,
        doc_type=doc_type,
        storage_key="",  # set after we know the id
        mime_type=mime_type,
        status="uploaded",
        uploaded_by=user_id,
    )
    db.add(doc)
    db.flush()

    storage_key = f"references/{exam_id}/{doc.id}.{ext}"
    storage.save(storage_key, content, content_type=mime_type)
    doc.storage_key = storage_key
    db.commit()
    db.refresh(doc)

    submit_job(process_reference_document, doc.id)
    return _serialize_doc(doc)


def list_reference_documents(db: Session, exam_id: int) -> List[Dict[str, Any]]:
    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(code="NOT_FOUND", message="Exam not found", status_code=404)
    docs = db.scalars(
        select(ReferenceDocument)
        .where(ReferenceDocument.exam_id == exam_id)
        .order_by(ReferenceDocument.created_at.desc())
    ).all()
    return [_serialize_doc(d) for d in docs]


def delete_reference_document(db: Session, doc_id: int) -> None:
    doc = db.get(ReferenceDocument, doc_id)
    if not doc:
        raise AppError(code="NOT_FOUND", message="Reference document not found", status_code=404)

    exam = db.get(Exam, doc.exam_id)
    if exam and exam.status != "draft":
        # IN_USE per api-spec.md D3: a reference_grounded question may depend
        # on it once the exam has moved past draft.
        dependent = db.scalar(
            select(Question).where(
                Question.exam_id == doc.exam_id, Question.evaluation_mode == "reference_grounded"
            )
        )
        if dependent:
            raise AppError(
                code="IN_USE",
                message="Cannot delete: a reference_grounded question may depend on this document "
                "and the exam is past draft",
                status_code=409,
            )

    try:
        namespace = doc.pinecone_namespace or f"exam-{doc.exam_id}"
        get_vector_store().delete_by_doc(namespace, doc.id)
    except RagError:
        # Best-effort: don't block deleting the DB record if the vector store
        # is unreachable — an orphaned vector is a much smaller problem than
        # being unable to delete a document at all.
        pass

    db.delete(doc)
    db.commit()


def search_reference(
    db: Session,
    exam_id: int,
    query: str,
    question_id: Optional[int],
    top_k: int,
) -> List[Dict[str, Any]]:
    """D5: debug/preview tool — embeds `query` directly rather than a question+rubric."""
    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(code="NOT_FOUND", message="Exam not found", status_code=404)

    any_indexed = db.scalar(
        select(ReferenceDocument).where(
            ReferenceDocument.exam_id == exam_id, ReferenceDocument.status == "indexed"
        )
    )
    if not any_indexed:
        raise AppError(
            code="NO_INDEXED_DOCUMENTS",
            message="No indexed reference documents exist for this exam",
            status_code=409,
        )

    try:
        embedding = get_embedding_provider().embed(query)
        namespace = f"exam-{exam_id}"
        qid_filter = [question_id, 0] if question_id is not None else None
        chunks = get_vector_store().query(namespace, embedding.vector, top_k, qid_filter)
    except RagError as exc:
        raise AppError(
            code="VECTOR_STORE_UNAVAILABLE", message=str(exc), status_code=503
        )

    doc_ids = {c.doc_id for c in chunks}
    docs = {
        d.id: d.title
        for d in db.scalars(select(ReferenceDocument).where(ReferenceDocument.id.in_(doc_ids))).all()
    }

    return [
        {
            "doc_id": c.doc_id,
            "title": docs.get(c.doc_id, c.title or "reference"),
            "chunk_index": c.chunk_index,
            "score": c.score,
            "text": c.text,
        }
        for c in chunks
    ]
