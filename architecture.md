# architecture.md

## 1. Overview

One React single-page app talks to **one** FastAPI service. The service uses PostgreSQL for data and calls four external cloud services: OCR, LLM, embeddings, and (optionally) Pinecone.

```
 Browser (React + Vite SPA)
        │  HTTPS, JSON, JWT
        ▼
 ┌──────────────────────────────── FastAPI (single service) ─────────────────────────────┐
 │  api/ (routers) ─▶ services/ (business rules) ─▶ models/ (SQLAlchemy)                  │
 │                         │                                                              │
 │                         └─▶ ai/  ocr · llm · rag · evaluation · anomaly · summaries    │
 └───────┬─────────────┬───────────────┬──────────────┬───────────────┬──────────────────┘
         ▼             ▼               ▼              ▼               ▼
    PostgreSQL   Storage (files)   OCR API        LLM API     Embedding API + Pinecone
    (cloud)      local → bucket    (adapter)      (adapter)   (optional, reference only)
```

Everything outside the FastAPI box is a managed service. The developer's laptop runs only the React dev server and the FastAPI process.

## 2. Components

| Component | Responsibility | Notes |
|---|---|---|
| React SPA | All UI for the three roles | Polls for progress; mobile-friendly examiner workspace |
| FastAPI app | REST API, auth, business rules, background jobs | Single deployable |
| PostgreSQL | All application data | Managed (Neon/Supabase) |
| StorageService | Answer-sheet images, reference files | Local disk in dev; S3-compatible bucket when deployed |
| OCRProvider | Image → text + confidence | Default Google Cloud Vision; replaceable |
| LLMClient | Prompt → validated JSON | Provider chosen by env |
| EmbeddingProvider + VectorStore | Reference chunks ↔ Pinecone | Used only for reference documents and reference-grounded questions |
| Anomaly engine | Statistical checks over marks | Pure Python + SQL aggregates |

## 3. Module map (the 13 required modules)

| # | Module | Backend location | Frontend area |
|---|---|---|---|
| 1 | Authentication & RBAC | `core/security.py`, `api/v1/auth.py`, `users.py` | Login, route guards |
| 2 | Examination management | `services/exam_service.py` | Exam management |
| 3 | Question & rubric management | `services/question_service.py` | Question/rubric editor |
| 4 | Answer sheet management | `services/sheet_service.py`, `storage_service.py` | Upload + page mapping, viewer |
| 5 | OCR / digitization | `ai/ocr/` | OCR status, correction panel |
| 6 | AI evaluation engine | `ai/evaluation/` | AI suggestion panel |
| 7 | Optional RAG / Pinecone layer | `ai/rag/` | Reference documents screen |
| 8 | Examiner workspace | `services/marking_service.py` | Workspace |
| 9 | Anomaly detection | `ai/anomaly/` | Flags in dashboards |
| 10 | Examiner analytics | `services/analytics_service.py` | Analytics |
| 11 | Moderation | `services/moderation_service.py` | Moderator dashboard |
| 12 | Result processing | `services/result_service.py` | Results dashboard |
| 13 | Dashboards | `analytics_service.py` + polling endpoints | Admin / examiner / moderator dashboards |

## 4. Roles and permissions (RBAC)

| Capability | Admin | Examiner | Moderator |
|---|:-:|:-:|:-:|
| Manage users, exams, questions, rubrics | ✔ | | |
| Upload sheets, map pages, assign examiners | ✔ | | |
| Upload reference documents, test retrieval | ✔ | | |
| Run OCR / AI evaluation in bulk | ✔ | | |
| View **assigned** answers, correct OCR, run AI on own answers | | ✔ | |
| Accept / modify / enter marks (assigned answers only) | | ✔ | |
| View flagged answers, compare marks, finalize moderated marks | | | ✔ |
| Run anomaly detection, view analytics | ✔ | own progress only | ✔ |
| Compute / publish results | ✔ | | |
| See student name and roll number | ✔ | | |

Examiners and moderators see only `anon_code` (blind marking, D-07). Access to an answer or page image is checked against `answers.assigned_examiner_id` for examiners.

## 5. Exam lifecycle

```
draft ──▶ evaluation ──▶ moderation ──▶ completed
```

| Transition | Preconditions (checked by `POST /exams/{id}/transition`) |
|---|---|
| draft → evaluation | ≥1 question; every question has a rubric whose criteria sum equals `max_marks`; every `reference_grounded` question has ≥1 indexed reference document; ≥1 sheet mapped and answers assigned |
| evaluation → moderation | Anomaly detection runs automatically. Unmarked attempted answers are allowed but reported |
| moderation → completed | No attempted answers with `marking_status = pending`; no open anomalies of severity `high` |

| Data | draft | evaluation | moderation | completed |
|---|:-:|:-:|:-:|:-:|
| Questions / rubrics editable | ✔ | | | |
| Sheets uploadable / mappable | ✔ | ✔ (unmarked answers only) | | |
| Examiner marks editable | | ✔ | | |
| Moderation decisions | | | ✔ | |
| Results computable | | | ✔ | ✔ |

## 6. Main data flows

**A. Setup (admin):** create exam → questions → rubrics → (optional) upload reference docs → upload answer-sheet pages per student → map page ranges to questions → assign examiners → transition to `evaluation`.

**B. Digitization:** `POST ocr/run` queues answers → background job preprocesses image, calls OCR, stores `ocr_text`, `ocr_confidence`, `ocr_review_required`.

**C. AI suggestion:** for each answer, evaluation mode is read from its question. Standard mode builds the prompt from question + effective text + rubric. Reference-grounded mode first retrieves chunks from Pinecone. The LLM returns JSON, the backend validates and stores an immutable `ai_evaluations` row.

**D. Human marking:** the examiner opens the workspace, checks or corrects OCR text, reads the AI suggestion, then **accepts**, **modifies** or enters marks **manually**, and submits. The backend writes `evaluations` and sets `answers.final_marks`, `marking_status = marked`.

**E. Monitoring:** anomaly detection compares marks with question and examiner baselines and looks for unchecked or missing marks. Flags appear in dashboards, and flagged answers get `marking_status = flagged`.

**F. Moderation:** the moderator opens a flagged answer, sees the image, OCR text, rubric, AI reasoning and the examiner's marks, then confirms or overrides. `moderations` is written, `final_marks` updated, `marking_status = moderated`, the anomaly is `resolved`.

**G. Results:** compute totals from `answers.final_marks` per student → `results` (draft) → admin publishes.

## 7. Evaluation mode decision logic

```
for answer:
    question = answer.question
    if question.evaluation_mode == "standard":
        prompt = Question + EffectiveText + Rubric                       # no Pinecone call
    else:  # reference_grounded
        chunks = pinecone.retrieve(question + rubric criteria, filter exam/question)
        if chunks above min_score exist:
            prompt = Question + EffectiveText + Rubric + Chunks
            mode_used = "reference_grounded"
        else:
            prompt = Question + EffectiveText + Rubric                   # graceful fallback
            mode_used = "standard"; warnings += ["NO_REFERENCE_FOUND"]
```

`mode_used` is stored with every AI evaluation. If Pinecone is down, reference-grounded questions fall back to standard with a `REFERENCE_UNAVAILABLE` warning, so the exam never blocks.

## 8. Background jobs (no queue server)

- Batch endpoints (`ocr/run`, `ai-evaluation/run`) return `202` immediately and hand work to a `ThreadPoolExecutor` (max 4 workers) so external API rate limits are respected.
- Job state lives in the data itself (`answers.ocr_status`, `answers.ai_status`). There is no job table.
- The frontend polls `GET /exams/{id}/processing-status`.
- After a server restart, unfinished items stay `pending`. Re-running the batch endpoint is idempotent and picks them up.

## 9. Security

- Passwords hashed with bcrypt. JWT (HS256) access token, 8-hour lifetime, no refresh token in MVP.
- Every route declares its allowed roles through a dependency. Row-level checks (assignment) live in services.
- Upload validation: allowed MIME types (JPEG, PNG, PDF for sheets; PDF, DOCX, TXT for references), max size 15 MB per file, server-generated storage keys, images served only through authenticated endpoints.
- **Prompt-injection defence:** student text is wrapped in delimiters and labelled as untrusted data. The LLM output is schema-validated, and an LLM can never write to the database directly.
- Secrets only in environment variables. CORS restricted to the frontend origin.

## 10. Deployment (demo)

| Piece | Suggested host |
|---|---|
| Frontend | Vercel or Netlify (static build) |
| Backend | Render, Railway or Fly.io (build from `requirements.txt`, no Docker needed) |
| PostgreSQL | Neon or Supabase (free tier) |
| File storage | S3-compatible bucket (Cloudflare R2, Supabase Storage or S3) |
| Vector DB | Pinecone serverless |

Local development needs Node and Python only. The database is the cloud instance. A local PostgreSQL is an optional alternative.

## 11. Technology justification ("Does this directly help the workflow?")

| Technology | Included? | Reason |
|---|---|---|
| Alembic | Yes | Schema changes are frequent; protects the shared cloud DB |
| PyMuPDF | Yes | Converts uploaded PDFs to page images with pip-only install |
| Pillow | Yes | Light image preprocessing before OCR |
| LangChain | Only text splitter | Chunking for reference documents; the evaluation call is a plain LLM call |
| Pinecone | Optional | Reference-grounded mode only |
| pandas / NumPy | No | SQL aggregates plus Python `statistics` are enough |
| Celery / Redis | No | Thread pool + status columns cover the need |
| WebSockets | No | Polling meets the "real-time" dashboard requirement |
| Docker / Kubernetes | No | Not needed for the workflow |
| Local vector DB (Chroma) | No | Explicitly replaced by Pinecone |

## 12. Known limitations (state them in the demo)

- Handwriting OCR quality varies. Low-confidence answers require human verification.
- AI marks are suggestions. Confidence is a triage signal, not a probability of being right.
- Page-to-question mapping is manual in the MVP.
- Anomaly flags are statistical hints; small samples (fewer than 10) produce no flags.
