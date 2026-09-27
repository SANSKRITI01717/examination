"""
Reference documents API router (D1, D2, D3, D5).
Contract: api-spec.md §11. D4 (reindex) is SHOULD HAVE and not built here.
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.core.storage import get_storage
from app.core.storage.base import StorageService
from app.models.user import User
from app.schemas.reference import (
    ReferenceDocumentResponse,
    ReferenceSearchRequest,
    ReferenceSearchResponse,
)
from app.services.reference_service import (
    delete_reference_document,
    list_reference_documents,
    search_reference,
    upload_reference_document,
)

router = APIRouter(tags=["Reference Documents"])


@router.post(
    "/exams/{id}/reference-documents",
    response_model=ReferenceDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_reference_document_endpoint(
    id: int,
    title: str = Form(...),
    doc_type: str = Form(...),
    question_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
    storage: StorageService = Depends(get_storage),
):
    """D1: Upload a reference file; chunking/embedding/upsert runs in the background."""
    return await upload_reference_document(
        db=db,
        exam_id=id,
        title=title,
        doc_type=doc_type,
        file=file,
        user_id=current_user.id,
        question_id=question_id,
        storage=storage,
    )


@router.get(
    "/exams/{id}/reference-documents",
    response_model=list[ReferenceDocumentResponse],
)
def list_reference_documents_endpoint(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """D2: List reference documents with status and chunk count."""
    return list_reference_documents(db=db, exam_id=id)


@router.delete(
    "/reference-documents/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_reference_document_endpoint(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """D3: Delete the file, DB row and its vectors."""
    delete_reference_document(db=db, doc_id=id)


@router.post(
    "/exams/{id}/reference-search",
    response_model=ReferenceSearchResponse,
)
def reference_search_endpoint(
    id: int,
    body: ReferenceSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """D5: Debug/preview retrieval tool."""
    chunks = search_reference(
        db=db, exam_id=id, query=body.query, question_id=body.question_id, top_k=body.top_k
    )
    return {"chunks": chunks}
