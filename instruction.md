# instruction.md — Read This First

> Every AI coding agent (Claude, Google Antigravity/Gemini) reads this file at the start of every session.
> Rules here override anything said in chat. Only the human owner may change this file.

## 1. Project in one paragraph

An AI-assisted digital examination and On-Screen Marking (OSM) platform for universities. Admins set up exams, questions and rubrics and upload scanned answer sheets. OCR turns handwriting into editable text. An LLM *suggests* marks against the rubric. The **examiner** accepts, modifies or overrides them. Statistical checks flag unchecked answers and unusual marking. A **moderator** resolves flagged cases. Results and analytics come from the final human-approved marks.

Target: a strong, demo-ready hackathon build that **one developer** can finish. Not a production-scale system.

## 2. Non-negotiable rules

1. **The examiner is the final authority.** AI only suggests. No code path may write final marks from an AI result without an explicit examiner (or moderator) action.
2. **RAG is optional and per-question.** Standard evaluation (Question + Answer + Rubric → LLM) must work with Pinecone completely switched off. Reference-grounded evaluation runs only when a question is configured with `evaluation_mode = reference_grounded`.
3. **A rubric is not RAG.** Rubrics are structured data in PostgreSQL and go straight into the prompt.
4. **Student answers never go into Pinecone.** Pinecone holds only reference material (official answers, guidelines, syllabus, faculty documents).
5. **PostgreSQL is the source of truth** for all application data.
6. **OCR is assistance, not truth.** Low OCR confidence must be shown clearly and require human verification before AI marks can be accepted.
7. **Validate all AI output** before storing it. Invalid output is rejected, never stored.
8. **Keep it simple.** See the anti-overengineering test (section 9).
9. **Do not silently change the stack.** Any change goes in the decision log (section 11) and needs owner approval.
10. **Do not write outside your ownership area** (section 7).

## 3. Locked technology stack

| Layer | Choice |
|---|---|
| Frontend | React + Vite + TypeScript + Tailwind CSS + Recharts + React Router + TanStack Query |
| Backend | Python, FastAPI, SQLAlchemy 2.0 (sync), Pydantic, Alembic |
| Database | PostgreSQL (managed cloud instance, e.g. Neon or Supabase) |
| Auth | JWT access token, role-based access control (admin, examiner, moderator) |
| LLM | Provider-agnostic `LLMClient` adapter; structured JSON output; model set in env |
| OCR | Replaceable `OCRProvider` adapter; default Google Cloud Vision `DOCUMENT_TEXT_DETECTION` |
| Vector DB | **Pinecone** (one index, one namespace per exam), optional |
| Embeddings | Cloud embedding API behind `EmbeddingProvider` adapter |
| RAG glue | LangChain **only** for text splitting (and optionally the Pinecone wrapper). Not used for the evaluation chain. |
| File storage | `StorageService` interface: local disk for dev, S3-compatible bucket for the deployed demo |
| Background work | FastAPI `BackgroundTasks` + a small thread pool. No queue server. |
| "Real-time" | Frontend polling (10–15 s). No WebSockets. |

**Explicitly excluded:** microservices, Kafka, Redis, Celery, Kubernetes, Docker orchestration, event buses, custom ML/OCR training, local vector DB, GraphQL.

## 4. The two evaluation modes

```
STANDARD            Question + Student Answer + Rubric ───────────────▶ LLM ▶ validated JSON
REFERENCE-GROUNDED  Question + Student Answer + Rubric + Pinecone chunks ▶ LLM ▶ validated JSON
```

Mode is a property of the **question** (`questions.evaluation_mode`, default `standard`). Details in `ai-pipeline.md`.

## 5. Data placement

| Data | Where |
|---|---|
| users, students, exams, questions, rubrics, answer sheets, answers, marks, AI evaluations, moderation, anomalies, results, summaries | PostgreSQL |
| Scanned images, uploaded reference files | Object/file storage (`StorageService`) |
| Chunked, embedded reference material | Pinecone |

## 6. Scope tiers

- **MVP:** auth/RBAC, exam/question/rubric management, answer upload + page mapping, OCR + correction, standard AI evaluation, optional reference-grounded mode, examiner workspace, unchecked-answer detection, basic anomaly detection (6 detectors), moderation, results, analytics dashboard, seed/demo data.
- **SHOULD HAVE:** AI summaries, extra detectors, CSV student import, results CSV export, keyboard shortcuts, auto page-to-question suggestion, LLM-vision OCR fallback, per-examiner drill-down analytics.
- **FUTURE:** ML anomaly model, double-blind marking, send-back-to-examiner, audit-log UI, multi-university tenancy, WebSockets.

Endpoint IDs in `api-spec.md` and phase steps in `development-phases.md` are tagged accordingly.

## 7. Ownership boundaries

| Area | Owner | Other agent may |
|---|---|---|
| `backend/**` | **Claude** | read only |
| `PROJECT/architecture.md`, `database-schema.md`, `api-spec.md`, `ai-pipeline.md`, `backend-plan.md`, `development-phases.md` | **Claude** | read only; propose changes via Contract Requests |
| `frontend/**` | **Antigravity/Gemini** | read only |
| `PROJECT/frontend-plan.md` | **Antigravity/Gemini** | read only |
| `PROJECT/instruction.md`, `README.md` | **Human owner** | read only |

**Contract-first handoff**
1. `api-spec.md` is the only contract between frontend and backend. Claude updates it *before* changing an endpoint.
2. Claude exports `backend/openapi.json` (generated by FastAPI). Gemini generates TypeScript types from it and never hand-writes API types.
3. If the frontend needs a change, Gemini writes a **Contract Request** (one paragraph: what, why, proposed shape) in the chat with the human owner. Claude updates the spec and implements it.
4. While the backend is unfinished, the frontend uses fixtures copied from the examples in `api-spec.md` (`VITE_USE_MOCK=true`).
5. Never edit the other agent's directories, even to "fix a small thing".

## 8. Working agreement (keeps sessions short and focused)

- One session = one **phase step** from `development-phases.md`. Do not start the next step in the same session.
- At session start read: this file + the one doc for the task (e.g. `database-schema.md` for a DB task). Do not load every file.
- At session end: tick the step in the `development-phases.md` progress checklist and list what the next session should start with.
- Prefer small vertical slices that run end to end over broad scaffolding.
- Do not generate code for modules outside the current step.
- If a requirement is ambiguous, pick the simplest interpretation, note it in the decision log, and continue.

## 9. Anti-overengineering test

Before adding any technology, table, endpoint, screen or abstraction ask:

> **"Does this directly help the required workflow?"**

If the answer is not clearly *yes*, do not add it. Production-style patterns are not a reason. Adapters exist only where the user explicitly wants replaceability (OCR, LLM, embeddings, storage).

## 10. Definition of done (per task)

- Follows the spec docs; endpoint behaviour matches `api-spec.md` exactly.
- Runs locally against the cloud DB with `.env` values only (no secrets in code).
- Has minimal tests for business rules (marks validation, AI output validation, anomaly detectors, result calculation).
- Frontend: handles loading, empty and error states; works at mobile width.
- The AI-is-an-assistant wording is visible wherever AI output is shown.

## 11. Decision log

| ID | Decision | Reason |
|---|---|---|
| D-01 | Sync SQLAlchemy + thread pool for background jobs | Simplest correct option for one developer; no queue server |
| D-02 | Polling for dashboards | "Real-time enough" without WebSocket complexity |
| D-03 | One rubric per question; criteria stored as JSONB | Rubrics are always read as a whole |
| D-04 | LLM returns only per-criterion marks, reasons, confidence. Backend computes totals and fills names/max marks | Removes arithmetic errors; easy to validate |
| D-05 | AI suggestions (`ai_evaluations`) and human marks (`evaluations`) are separate tables | AI stays an immutable audit record; humans own final marks |
| D-06 | MVP answer extraction = admin maps page ranges to questions; auto-suggest is SHOULD HAVE | Automatic segmentation of handwritten sheets is unreliable |
| D-07 | Blind marking: examiners and moderators see `anon_code`, never student name or roll number | Standard university practice; cheap to implement |
| D-08 | No repositories layer; services use SQLAlchemy sessions directly | Extra layer is boilerplate for this size |
| D-09 | TypeScript frontend with types generated from OpenAPI | Prevents contract drift between the two agents |
| D-10 | Default OCR: Google Cloud Vision behind an adapter | Per-word confidence, handwriting support, no local models |
| D-11 | Alembic from day one | Two agents and a cloud DB make schema changes frequent |
| D-12 | One Pinecone index, namespace per exam | Isolation and easy cleanup |
| D-13 | Local file storage for dev only; bucket for deployed demo | Free hosts have ephemeral disks |
| D-14 | Pinecone metadata stores the chunk text | Retrieval needs no second lookup |

## 12. Document map

| Need | File |
|---|---|
| System overview, components, RBAC, flows | `architecture.md` |
| Tables, columns, enums, invariants | `database-schema.md` |
| Every endpoint with auth, request, response, errors | `api-spec.md` |
| OCR, LLM, RAG, anomaly detection explained | `ai-pipeline.md` |
| Backend structure, services, config | `backend-plan.md` |
| Screens, routes, components, mocks | `frontend-plan.md` |
| Build order, exit criteria, progress checklist | `development-phases.md` |
| Human-facing overview and setup | `README.md` |

## 13. Glossary

- **OSM:** On-Screen Marking, where examiners mark scanned scripts on a screen.
- **Rubric:** structured marking scheme (criteria + marks) for one question.
- **Reference material:** official answers or guidelines used only in reference-grounded mode.
- **RAG:** retrieving relevant reference chunks and giving them to the LLM as context.
- **Effective text:** `verified_text` if the examiner corrected the OCR, otherwise `ocr_text`.
- **Unchecked answer:** an attempted answer with no submitted examiner marks, or marks submitted implausibly fast.
- **Anomaly:** a statistical flag that asks a human to look. It is never an accusation.
