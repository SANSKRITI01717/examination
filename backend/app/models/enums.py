"""
Canonical enum definitions for all SQLAlchemy models.
Stored as VARCHAR with CHECK constraints (native_enum=False) per database-schema.md §1.
"""
from sqlalchemy import Enum as SAEnum


def _enum(*values, name=None):
    return SAEnum(*values, native_enum=False, create_constraint=True)


# --- Users ---
user_role = _enum("admin", "examiner", "moderator", name="user_role")

# --- Exams ---
exam_status = _enum("draft", "evaluation", "moderation", "completed", name="exam_status")
evaluation_mode = _enum("standard", "reference_grounded", name="evaluation_mode")

# --- Sheets ---
sheet_status = _enum("uploaded", "mapped", name="sheet_status")

# --- Answers: OCR state ---
ocr_status = _enum("pending", "processing", "done", "failed", name="ocr_status")

# --- Answers: AI state ---
ai_status = _enum(
    "not_requested", "pending", "processing", "done", "failed",
    name="ai_status",
)

# --- Answers: marking state ---
marking_status = _enum("pending", "marked", "flagged", "moderated", name="marking_status")
final_source = _enum("examiner", "moderator", "system", name="final_source")

# --- Evaluations ---
evaluation_source = _enum("ai_accepted", "ai_modified", "manual", name="evaluation_source")
evaluation_status = _enum("draft", "submitted", name="evaluation_status")

# --- Reference documents ---
doc_type = _enum("official_answer", "guideline", "syllabus", "other", name="doc_type")
doc_status = _enum("uploaded", "indexing", "indexed", "failed", name="doc_status")

# --- Anomalies ---
anomaly_type = _enum(
    "UNCHECKED_ANSWER",
    "MISSING_MARKS",
    "QUESTION_OUTLIER",
    "EXAMINER_DEVIATION",
    "AI_DISAGREEMENT",
    "TOO_FAST",
    # SHOULD HAVE:
    "SCORE_SHIFT",
    "REPEATED_PATTERN",
    "UNVERIFIED_OCR",
    name="anomaly_type",
)
anomaly_severity = _enum("low", "medium", "high", name="anomaly_severity")
anomaly_status = _enum("open", "dismissed", "resolved", name="anomaly_status")

# --- Moderation ---
moderation_decision = _enum("confirmed", "overridden", name="moderation_decision")

# --- Results ---
result_status = _enum("draft", "published", name="result_status")

# --- Summaries ---
summary_scope = _enum("exam", "examiner", name="summary_scope")
