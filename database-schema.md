# database-schema.md

PostgreSQL, managed through SQLAlchemy 2.0 models and Alembic migrations.

## 1. Conventions

- Primary keys: `BIGINT` identity named `id`.
- Timestamps: `TIMESTAMPTZ`, UTC, `created_at` defaults to `now()`.
- Marks: `NUMERIC(5,2)`. Confidence: `NUMERIC(4,3)` in 0–1.
- Enums: stored as `VARCHAR` with a `CHECK` constraint (SQLAlchemy `Enum(native_enum=False)`) so Alembic stays simple.
- `PK` primary key, `FK→t.c` foreign key, `UQ` unique. Nullable columns are marked `null`.
- No hard deletes of users, exams, answers or marks. Deactivate instead (`is_active`). Exceptions: questions in a `draft` exam and reference documents.

## 2. Relationships

```
users ─┬─< exams ─┬─< questions ──1:1── rubrics
       │          ├─< reference_documents
       │          ├─< answer_sheets >── students
       │          │        ├─< answer_sheet_pages
       │          │        └─< answers >── questions
       │          │              ├─< ai_evaluations      (immutable AI suggestions)
       │          │              ├─0..1 evaluations      (examiner marks)
       │          │              └─< moderations         (moderator decisions)
       │          ├─< anomalies
       │          ├─< results >── students
       │          └─< ai_summaries
```

Derived data such as question means, examiner statistics and histograms is **not stored**. It is computed on demand with SQL aggregates.

## 3. Enums (canonical, used by the API and the UI)

| Enum | Values |
|---|---|
| `user_role` | `admin`, `examiner`, `moderator` |
| `exam_status` | `draft`, `evaluation`, `moderation`, `completed` |
| `evaluation_mode` | `standard`, `reference_grounded` |
| `sheet_status` | `uploaded`, `mapped` |
| `ocr_status` | `pending`, `processing`, `done`, `failed` |
| `ai_status` | `not_requested`, `pending`, `processing`, `done`, `failed` |
| `marking_status` | `pending`, `marked`, `flagged`, `moderated` |
| `final_source` | `examiner`, `moderator`, `system` (system = not attempted, 0 marks) |
| `evaluation_source` | `ai_accepted`, `ai_modified`, `manual` |
| `evaluation_status` | `draft`, `submitted` |
| `doc_type` | `official_answer`, `guideline`, `syllabus`, `other` |
| `doc_status` | `uploaded`, `indexing`, `indexed`, `failed` |
| `anomaly_type` | `UNCHECKED_ANSWER`, `MISSING_MARKS`, `QUESTION_OUTLIER`, `EXAMINER_DEVIATION`, `AI_DISAGREEMENT`, `TOO_FAST` (MVP); `SCORE_SHIFT`, `REPEATED_PATTERN`, `UNVERIFIED_OCR` (SHOULD HAVE) |
| `anomaly_severity` | `low`, `medium`, `high` |
| `anomaly_status` | `open`, `dismissed`, `resolved` |
| `moderation_decision` | `confirmed`, `overridden` |
| `result_status` | `draft`, `published` |
| `summary_scope` | `exam`, `examiner` |

## 4. Tables

### users
Purpose: login accounts for all three roles.

| Column | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| email | VARCHAR(255) | UQ, lowercase |
| password_hash | VARCHAR(255) | bcrypt |
| full_name | VARCHAR(150) | |
| role | user_role | |
| is_active | BOOLEAN | default true |
| created_at | TIMESTAMPTZ | |

Indexes: UQ(email), (role).

### exams
Purpose: one examination and its configuration.

| Column | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| title | VARCHAR(200) | |
| course_code | VARCHAR(50) | |
| exam_date | DATE | null |
| status | exam_status | default `draft` |
| settings | JSONB | thresholds, see below |
| created_by | BIGINT | FK→users.id |
| created_at | TIMESTAMPTZ | |

`settings` defaults (each overridable per exam):
`ocr_low_conf_threshold 0.80`, `ai_low_conf_threshold 0.70`, `ai_disagreement_ratio 0.30`, `too_fast_seconds 10`, `z_threshold 2.5`, `min_sample_size 10`, `retrieval_top_k 4`, `retrieval_min_score 0.50`.

Indexes: (status).

### questions
Purpose: a question in an exam and its evaluation mode.

| Column | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| exam_id | BIGINT | FK→exams.id |
| question_number | VARCHAR(10) | label such as `1`, `2a` |
| text | TEXT | |
| max_marks | NUMERIC(5,2) | |
| evaluation_mode | evaluation_mode | default `standard` |
| display_order | INT | |

Indexes: UQ(exam_id, question_number).

### rubrics
Purpose: the structured marking scheme for one question (**not** RAG).

| Column | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| question_id | BIGINT | FK→questions.id, UQ |
| criteria | JSONB | `[{"id":"c1","name":"SYN sent","max_marks":2,"description":"..."}]` |
| guidance | TEXT | null. Free-text notes such as "accept alternative wording" |
| updated_at | TIMESTAMPTZ | |

Rule: `sum(criteria[].max_marks) == questions.max_marks`. Criterion ids are stable strings (`c1`, `c2`, …) and are what the LLM references.

### students
Purpose: candidates. Visible to admins only.

| Column | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| roll_number | VARCHAR(50) | UQ |
| full_name | VARCHAR(150) | |
| department | VARCHAR(100) | null |
| created_at | TIMESTAMPTZ | |

### answer_sheets
Purpose: one student's scanned script for one exam.

| Column | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| exam_id | BIGINT | FK→exams.id |
| student_id | BIGINT | FK→students.id |
| anon_code | VARCHAR(20) | e.g. `S-0417`, shown to examiners |
| status | sheet_status | default `uploaded` |
| uploaded_by | BIGINT | FK→users.id |
| created_at | TIMESTAMPTZ | |

Indexes: UQ(exam_id, student_id), UQ(exam_id, anon_code).

### answer_sheet_pages
Purpose: the image of each page. Justified because a sheet has many pages.

| Column | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| answer_sheet_id | BIGINT | FK→answer_sheets.id |
| page_number | INT | starts at 1 |
| storage_key | VARCHAR(300) | `sheets/{exam_id}/{sheet_id}/page_{n}.jpg` |
| width, height | INT | pixels |

Indexes: UQ(answer_sheet_id, page_number).

### answers
Purpose: one student's response to one question. It is the central working row (OCR state, AI state, marking state).

| Column | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| exam_id | BIGINT | FK→exams.id (denormalized for fast filtering and analytics) |
| answer_sheet_id | BIGINT | FK→answer_sheets.id |
| question_id | BIGINT | FK→questions.id |
| page_start, page_end | INT | page range on the sheet |
| is_attempted | BOOLEAN | default true |
| ocr_status | ocr_status | default `pending` |
| ocr_text | TEXT | null. Raw OCR output |
| ocr_confidence | NUMERIC(4,3) | null |
| ocr_review_required | BOOLEAN | default false |
| ocr_verified | BOOLEAN | default false. Examiner confirmed the text |
| verified_text | TEXT | null. Examiner-corrected text |
| ocr_meta | JSONB | null. Low-confidence word count, provider name, etc. |
| ai_status | ai_status | default `not_requested` |
| ai_error | TEXT | null |
| assigned_examiner_id | BIGINT | FK→users.id, null |
| marking_status | marking_status | default `pending` |
| final_marks | NUMERIC(5,2) | null. **Written only by MarkingService / ModerationService** |
| final_source | final_source | null |
| created_at, updated_at | TIMESTAMPTZ | |

Indexes: UQ(answer_sheet_id, question_id); (exam_id, assigned_examiner_id, marking_status); (exam_id, question_id); (exam_id, ocr_status); (exam_id, ai_status).

### ai_evaluations
Purpose: immutable AI suggestions (history is kept when re-run).

| Column | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| answer_id | BIGINT | FK→answers.id |
| mode_requested | evaluation_mode | |
| mode_used | evaluation_mode | differs if reference retrieval fell back |
| model_name | VARCHAR(100) | |
| prompt_version | VARCHAR(30) | e.g. `eval_v1` |
| input_hash | CHAR(64) | sha256(effective text + rubric + mode + prompt_version). Used for cache and stale detection |
| suggested_marks | NUMERIC(5,2) | sum of criteria, computed by backend |
| max_marks | NUMERIC(5,2) | |
| confidence | NUMERIC(4,3) | effective confidence (see `ai-pipeline.md`) |
| llm_confidence | NUMERIC(4,3) | as reported by the LLM |
| criteria | JSONB | `[{"criterion_id","criterion","max_marks","awarded_marks","reason"}]` |
| overall_reason | TEXT | |
| retrieval | JSONB | null. `[{"doc_id","chunk_index","score","snippet"}]` |
| warnings | JSONB | e.g. `["LOW_CONFIDENCE","LOW_OCR_CONFIDENCE","NO_REFERENCE_FOUND","REFERENCE_UNAVAILABLE"]` |
| latency_ms | INT | |
| triggered_by | BIGINT | FK→users.id, null (null = batch job) |
| created_at | TIMESTAMPTZ | |

Indexes: (answer_id, created_at DESC).

### evaluations
Purpose: the examiner's marks. This is a human decision, never written by AI code.

| Column | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| answer_id | BIGINT | FK→answers.id, UQ |
| examiner_id | BIGINT | FK→users.id |
| ai_evaluation_id | BIGINT | FK→ai_evaluations.id, null |
| marks_awarded | NUMERIC(5,2) | |
| criterion_marks | JSONB | null. `[{"criterion_id","awarded_marks"}]` |
| comment | TEXT | null |
| source | evaluation_source | |
| status | evaluation_status | |
| opened_at | TIMESTAMPTZ | first time the examiner opened the answer |
| active_seconds | INT | time reported by the client |
| submitted_at | TIMESTAMPTZ | null |
| created_at, updated_at | TIMESTAMPTZ | |

Indexes: (examiner_id, status).

### moderations
Purpose: moderator decisions. History is kept and the latest row wins.

| Column | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| answer_id | BIGINT | FK→answers.id |
| evaluation_id | BIGINT | FK→evaluations.id |
| moderator_id | BIGINT | FK→users.id |
| original_marks | NUMERIC(5,2) | |
| moderated_marks | NUMERIC(5,2) | |
| decision | moderation_decision | |
| reason | TEXT | required when `overridden` |
| created_at | TIMESTAMPTZ | |

Indexes: (answer_id, created_at DESC).

### anomalies
Purpose: statistical flags for humans to review.

| Column | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| exam_id | BIGINT | FK→exams.id |
| type | anomaly_type | |
| severity | anomaly_severity | |
| answer_id | BIGINT | FK→answers.id, null |
| question_id | BIGINT | FK→questions.id, null |
| examiner_id | BIGINT | FK→users.id, null |
| score | NUMERIC(8,3) | null. e.g. the z-score |
| details | JSONB | human-readable evidence (numbers used) |
| status | anomaly_status | default `open` |
| note | TEXT | null |
| dedupe_key | VARCHAR(120) | e.g. `TOO_FAST:answer:812`. Makes re-runs idempotent |
| detected_at | TIMESTAMPTZ | |
| resolved_by | BIGINT | FK→users.id, null |

Indexes: UQ(exam_id, dedupe_key); (exam_id, status, severity); (examiner_id).

### reference_documents
Purpose: registry of files whose chunks live in Pinecone. Pinecone holds vectors only, so this table is the source of truth for what was indexed.

| Column | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| exam_id | BIGINT | FK→exams.id |
| question_id | BIGINT | FK→questions.id, null (null = applies to the whole exam) |
| title | VARCHAR(200) | |
| doc_type | doc_type | |
| storage_key | VARCHAR(300) | |
| mime_type | VARCHAR(100) | |
| status | doc_status | default `uploaded` |
| chunk_count | INT | default 0 |
| pinecone_namespace | VARCHAR(50) | `exam-{exam_id}` |
| error | TEXT | null |
| uploaded_by | BIGINT | FK→users.id |
| created_at | TIMESTAMPTZ | |

Indexes: (exam_id, status), (question_id).

### results
Purpose: per-student total for an exam, computed from `answers.final_marks`.

| Column | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| exam_id | BIGINT | FK→exams.id |
| student_id | BIGINT | FK→students.id |
| total_marks | NUMERIC(6,2) | |
| max_marks | NUMERIC(6,2) | |
| percentage | NUMERIC(5,2) | |
| status | result_status | default `draft` |
| computed_at | TIMESTAMPTZ | |
| published_at | TIMESTAMPTZ | null |

Indexes: UQ(exam_id, student_id).

### ai_summaries
Purpose: stored AI-written narrative summaries. The numbers come from code, and the LLM only narrates them.

| Column | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| exam_id | BIGINT | FK→exams.id |
| scope | summary_scope | |
| examiner_id | BIGINT | FK→users.id, null (set when scope = `examiner`) |
| content | TEXT | |
| stats | JSONB | the exact statistics snapshot given to the LLM (auditable) |
| model_name | VARCHAR(100) | |
| created_by | BIGINT | FK→users.id |
| created_at | TIMESTAMPTZ | |

Indexes: (exam_id, scope, created_at DESC).

## 5. Pinecone (not a SQL table)

| Item | Value |
|---|---|
| Index | one serverless index, cosine metric, dimension = embedding model dimension |
| Namespace | `exam-{exam_id}` |
| Vector id | `{reference_document_id}:{chunk_index}` |
| Metadata | `exam_id`, `doc_id`, `question_id` (0 = whole exam), `doc_type`, `chunk_index`, `text` |
| Contents | reference material **only**. Never student answers |

## 6. Invariants (enforced in services and tests)

1. `sum(rubric criteria max_marks) == question.max_marks`.
2. `0 ≤ marks ≤ max_marks` for suggestions, examiner marks and moderated marks. Step 0.5 is allowed.
3. If `criterion_marks` is present, its sum equals `marks_awarded`.
4. `ai_evaluations` rows are never updated or deleted.
5. `answers.final_marks` is written only by MarkingService (examiner submit) or ModerationService (moderator decision). Not attempted answers get `final_marks = 0`, `final_source = system`, `marking_status = marked` when the sheet is mapped.
6. Effective text = `verified_text` if not null, else `ocr_text`.
7. An AI suggestion is **stale** when the input hash recomputed from the current effective text and rubric differs from `ai_evaluations.input_hash`. Stale suggestions cannot be accepted.
8. If `ocr_review_required = true` and `ocr_verified = false`, `accept-ai` is refused (manual and modified marks are still allowed).
9. Student identity fields are never returned to examiner or moderator endpoints.
10. Deleting a reference document deletes its Pinecone vectors first, then the row.
11. Pinecone vectors are created only from `reference_documents`.
