"""
Extract plain text from an uploaded reference document.
PDF uses PyMuPDF (fitz) — already a project dependency (used for answer-sheet
PDF splitting). DOCX uses python-docx — a NEW dependency, added explicitly
in requirements.txt for this step. TXT is a trivial decode.
"""
import io

import fitz  # PyMuPDF, already a dependency

from app.core.errors import AppError

_PDF_MIME = "application/pdf"
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_TXT_MIME = "text/plain"


def guess_mime_type(filename: str) -> str:
    """Used at upload time (D1) to validate + classify the file by its name."""
    lower = (filename or "").lower()
    if lower.endswith(".pdf"):
        return _PDF_MIME
    if lower.endswith(".docx"):
        return _DOCX_MIME
    if lower.endswith(".txt"):
        return _TXT_MIME
    raise AppError(
        code="UNSUPPORTED_FILE",
        message=f"Unsupported file type for '{filename}'. Allowed: PDF, DOCX, TXT",
        status_code=415,
    )


def extract_text(content: bytes, mime_type: str) -> str:
    """Used later by the background indexing job, keyed off the stored mime_type."""
    if mime_type == _PDF_MIME:
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text
        except Exception as exc:
            raise AppError(
                code="UNSUPPORTED_FILE",
                message=f"Failed to extract text from PDF: {exc}",
                status_code=415,
            )

    if mime_type == _DOCX_MIME:
        try:
            import docx  # python-docx — new dependency, see requirements.txt
        except ImportError as exc:
            raise AppError(
                code="UNSUPPORTED_FILE",
                message="python-docx is not installed; DOCX reference documents are unavailable",
                status_code=415,
            ) from exc
        try:
            document = docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in document.paragraphs)
        except Exception as exc:
            raise AppError(
                code="UNSUPPORTED_FILE",
                message=f"Failed to extract text from DOCX: {exc}",
                status_code=415,
            )

    if mime_type == _TXT_MIME:
        try:
            return content.decode("utf-8", errors="replace")
        except Exception as exc:
            raise AppError(
                code="UNSUPPORTED_FILE",
                message=f"Failed to decode text file: {exc}",
                status_code=415,
            )

    raise AppError(
        code="UNSUPPORTED_FILE",
        message=f"Unsupported file type '{mime_type}'. Allowed: PDF, DOCX, TXT",
        status_code=415,
    )
