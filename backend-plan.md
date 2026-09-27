# backend-plan.md

Owner: **Claude**. Stack and rules: `instruction.md`. System context: `architecture.md`.

## 1. Folder structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app, CORS, router mounting, error handlers
│   ├── core/
│   │   ├── config.py              # Pydantic Settings (env vars)
│   │   ├── db.py                  # engine, SessionLocal, get_db dependency
│   │   ├── security.py            # password hashing, JWT create/decode
│   │   ├── deps.py                # get_current_user, require_role(...)
│   │   └── errors.py              # AppError(code, message, status, details) + handler
│   ├── models/                    # SQLAlchemy models, one file per table group
│   │   ├── user.py  exam.py  question.py  student.py  sheet.py  answer.py
│   │   └── evaluation.py  moderation.py  anomaly.py  reference.py  result.py  summary.py
│   ├── schemas/                   # Pydantic request/response models, mirrors api-spec.md
│   ├── api/v1/                    # thin routers: parse → call service → return
│   │   ├── auth.py  users.py  exams.py  questions.py  students.py  sheets.py
│   │   ├── ocr.py  answers.py  ai_evaluation.py  reference_docs.py
│   │   ├── marks.py  moderation.py  anomalies.py  analytics.py  results.py
│   ├── services/                  # business rules, transactions, permissions (no AI internals)
│   │   ├── exam_service.py        # lifecycle + transition preconditions
│   │   ├── question_service.py    # questions + rubric validation
│   │   ├── sheet_service.py       # upload, PDF split, mapping, assignment
│   │   ├── storage_service.py     # StorageService interface + LocalStorage + S3Storage
│   │   ├── marking_service.py     # accept / modify / manual marks; sole writer of final_marks (examiner)
│   │   ├── moderation_service.py  # confirm / override; sole writer of final_marks (moderator)
│   │   ├── analytics_service.py   # SQL aggregates for dashboards + summary inputs
│   │   ├── result_service.py      # compute, publish, export
│   │   └── job_runner.py          # ThreadPoolExecutor(4) + batch helpers
│   ├── ai/                        # everything that calls OCR/LLM/embeddings/Pinecone
│   │   ├── ocr/
│   │   │   ├── base.py            # OCRProvider, OCRResult
│   │   │   ├── vision_provider.py # Google Cloud Vision (default)
│   │   │   ├── preprocess.py      # Pillow steps
│   │   │   └── confidence.py      # review_required rules
│   │   ├── llm/
│   │   │   ├── base.py            # LLMClient.generate_json(system, user, schema)
│   │   │   └── anthropic_client.py  gemini_client.py (optional)
│   │   ├── rag/
│   │   │   ├── embeddings.py      # EmbeddingProvider
│   │   │   ├── vector_store.py    # VectorStore interface + PineconeStore
│   │   │   ├── indexer.py         # extract → chunk → embed → upsert
│   │   │   └── retriever.py       # query building, filter, min_score
│   │   ├── evaluation/
│   │   │   ├── prompts.py         # versioned prompt templates
│   │   │   ├── evaluator.py       # mode selection, prompt, LLM call, repair retry
│   │   │   └── validator.py       # output validation + total computation
│   │   ├── anomaly/
│   │   │   ├── detectors.py       # one pure function per detector
│   │   │   └── runner.py          # loads data, runs detectors, upserts anomalies
│   │   └── summaries/summarizer.py
│   └── utils/                     # hashing, text helpers, time
├── alembic/  alembic.ini
├── scripts/seed_demo.py           # demo users, exam, rubrics, sample scans, fake OCR/AI outputs
├── tests/
├── requirements.txt
└── .env.example
```

**No `repositories/` layer** (D-08). Services use SQLAlchemy sessions directly. **AI code is isolated in `ai/`**: routers never call providers, and `ai/` never applies marks, so only `marking_service` and `moderation_service` write `final_marks`.

## 2. Layer rules

| Layer | May call | Must not |
|---|---|---|
| `api/` | `services/`, `schemas/`, `deps` | contain business logic, query SQL directly, call providers |
| `services/` | `models/`, `ai/` (through evaluator/indexer/runner entry points), storage | import FastAPI request objects |
| `ai/` | provider SDKs, `models/` read-only via arguments passed in | write `evaluations`, `moderations` or `answers.final_marks` |
| `models/` | – | contain business logic |

`ai/evaluation/evaluator.py` returns a validated in-memory result. `services/` persists it as an `ai_evaluations` row and updates `answers.ai_status`.

## 3. Adapters (the only abstractions)

| Interface | Implementations | Selected by env |
|---|---|---|
| `OCRProvider` | `VisionProvider` (default), later `AzureReadProvider`, `LLMVisionProvider` | `OCR_PROVIDER` |
| `LLMClient` | `AnthropicClient`, `GeminiClient` (optional) | `LLM_PROVIDER`, `LLM_MODEL` |
| `EmbeddingProvider` | one cloud embedding API | `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL` |
| `VectorStore` | `PineconeStore` | `PINECONE_*` |
| `StorageService` | `LocalStorage`, `S3Storage` | `STORAGE_BACKEND` |

Tests inject `FakeOCRProvider`, `FakeLLMClient`, `FakeVectorStore`, `MemoryStorage`. This also powers the demo seed script. If `PINECONE_API_KEY` is unset, reference-grounded questions fall back to standard mode with a warning and the reference upload endpoints return `503 VECTOR_STORE_UNAVAILABLE`. Everything else is unaffected.

## 3.1 Environment variables (`.env.example`)

```
DATABASE_URL=postgresql+psycopg://...
JWT_SECRET=...            JWT_EXPIRE_MINUTES=480
CORS_ORIGINS=http://localhost:5173
STORAGE_BACKEND=local     LOCAL_STORAGE_DIR=./storage      S3_BUCKET= S3_ENDPOINT= S3_KEY= S3_SECRET=
OCR_PROVIDER=vision       GOOGLE_APPLICATION_CREDENTIALS=...
LLM_PROVIDER=anthropic    LLM_MODEL=...     ANTHROPIC_API_KEY=...     (or GEMINI_API_KEY)
EMBEDDING_PROVIDER=...    EMBEDDING_MODEL=...   EMBEDDING_DIM=...
PINECONE_API_KEY=         PINECONE_INDEX=exam-references
MAX_UPLOAD_MB=15          JOB_WORKERS=4
```

Verify current model names and embedding dimensions at implementation time. The dimension must equal the Pinecone index dimension.

## 4. Key service responsibilities

| Service | Core methods (conceptual) | Rules enforced |
|---|---|---|
| `exam_service` | `transition(exam, to)` | Preconditions from `architecture.md` §5; runs anomaly detection on entering `moderation` |
| `question_service` | `upsert_rubric(q, criteria)` | Sum equals `max_marks`; unique criterion ids; exam must be `draft` |
| `sheet_service` | `upload(exam, student, files)`, `map(sheet, items)`, `assign(exam, examiners, strategy)` | Validate MIME/size; PDF → images (PyMuPDF); generate `anon_code`; unattempted answers get 0 marks with `final_source = system`; never remap a marked answer; round-robin assignment |
| `marking_service` | `accept_ai`, `save_or_submit` | Assignment check; OCR-verified guard; stale check via `input_hash`; range and criterion-sum validation; set `final_marks` and `marking_status`; record `opened_at` and `active_seconds` |
| `moderation_service` | `decide` | Exam must be `moderation`; override requires reason; sets final marks; resolves the answer's open anomalies |
| `evaluator` (ai) | `evaluate(answer, question, rubric, settings) -> AIResult` | Mode selection and fallback; prompt build; validation; one repair retry |
| `runner` (anomaly) | `run(exam, detectors)` | Upsert by `dedupe_key`; skip detectors below `min_sample_size` |
| `analytics_service` | `overview`, `examiners`, `questions`, `my_progress`, `stats_snapshot` | SQL aggregates only |
| `result_service` | `compute`, `publish`, `export_csv` | Sum `final_marks`; refuse if pending attempted answers or open high anomalies |

## 5. Background jobs

- `job_runner.submit(batch_fn, ids)` uses a module-level `ThreadPoolExecutor(JOB_WORKERS)`. Each task opens its own DB session.
- State lives on the rows: set `processing` → `done`/`failed`. Batch endpoints select rows in `pending`/`failed` only, so re-runs are idempotent.
- Reference indexing uses the same runner and updates `reference_documents.status`.
- Failure handling: catch per item, store the error (`ai_error`, `error`), never crash the batch.

## 6. Auth and RBAC implementation

- `require_role("admin")` dependency on each route (roles from the table in `architecture.md` §4).
- Row-level checks in services: examiner must equal `answers.assigned_examiner_id`. Sheet page images are served by AS5 after the same check.
- Response builders drop student fields unless the caller is admin (D-07).

## 7. Error handling

All errors raised as `AppError(code, message, status, details)` and rendered in the standard error body from `api-spec.md`. Validation errors from Pydantic map to `VALIDATION_ERROR`. External provider failures map to `502` (`LLM_UNAVAILABLE`, `OCR_UNAVAILABLE`) or `503` (`VECTOR_STORE_UNAVAILABLE`). No stack traces in responses.

## 8. Testing plan (pytest, minimal but meaningful)

| Area | Tests |
|---|---|
| Rubric | Sum mismatch, duplicate ids |
| Marks | Range, 0.5 steps, criterion sum, ownership, locked exam |
| AI validator | Valid, unknown criterion, out of range, missing criterion, computed total overrides LLM total |
| Evaluator | Standard mode makes **no** vector-store call; reference-grounded uses chunks; empty retrieval falls back with warning |
| Guards | `accept-ai` refused when OCR unverified or suggestion stale |
| OCR confidence | Threshold rules |
| Anomaly detectors | Each detector on synthetic data; sample size < 10 gives no flags; idempotent re-run |
| Results | Totals, incomplete marking refusal |
| Blind marking | Examiner payloads contain no student fields |

## 9. Delivery notes

- Generate `openapi.json` after each API change (`python scripts/export_openapi.py`) so the frontend can regenerate types.
- Order of implementation follows `development-phases.md`. One phase step per session.
- `scripts/seed_demo.py` is a first-class deliverable, because demos should not depend on live handwriting OCR.
