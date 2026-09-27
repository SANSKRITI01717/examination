# development-phases.md

Build in thin vertical slices. Each phase ends with something that runs. **One step per agent session** (see `instruction.md` §8). Effort: S ≈ half a day, M ≈ 1 day, L ≈ 2 days for a focused solo developer using two agents.

## 1. Scope tiers

| Tier | Contents |
|---|---|
| **MVP** | Auth/RBAC · users · exams · questions · rubrics · students · sheet upload + page mapping · assignment · OCR + correction · standard AI evaluation · optional reference-grounded mode (Pinecone) · examiner workspace · unchecked-answer detection · 6 basic anomaly detectors · moderation · results · analytics dashboard · seed/demo data |
| **SHOULD HAVE** | AI summaries (AL5, AL6) · CSV student import (S3) · results CSV export (RS5) · reindex (D4) · extra detectors (`SCORE_SHIFT`, `REPEATED_PATTERN`, `UNVERIFIED_OCR`) · auto page-to-question suggestion · LLM-vision OCR fallback · keyboard shortcuts |
| **FUTURE** | ML anomaly model · double marking · send-back-to-examiner · audit-log UI · multi-tenant · WebSockets |

If time runs short, cut from the bottom of the MVP list in this order: analytics polish → reference-grounded mode → extra detectors. The core loop (upload → OCR → AI suggestion → examiner decision → moderation → results) must survive.

## 2. Phase plan

| Phase | Claude (backend/AI) | Gemini (frontend) | Exit criteria | Effort |
|---|---|---|---|---|
| **0 Foundations** | Repo skeleton, config, DB connection, Alembic, `AppError`, health check, OpenAPI export, all models + first migration | Vite + TS + Tailwind, router, API client, mock layer, AppShell, UI primitives, type generation | Backend `/health` OK; frontend renders shell in mock mode; contract (`api-spec.md`) frozen for phases 1–3 | M |
| **1 Auth & users** (A1–A2, U1–U3) | JWT, bcrypt, `require_role`, seed admin | Login page, AuthProvider, ProtectedRoute, Users screen | Log in as each role and land on the right dashboard shell | S |
| **2 Exams, questions, rubrics** (E1–E5, Q1–Q4, R1–R2) | Services + validations + lifecycle preconditions | Exam list/detail, question + rubric editor (sum check, mode toggle), lifecycle stepper | Create an exam with rubric-validated questions and see transition failures listed | M |
| **3 Sheets, mapping, assignment** (S1–S2, AS1–AS6) | `StorageService` (local), upload, PDF split, `anon_code`, mapping, assignment | Sheet upload, page mapping UI, assignments screen | Upload a scan, map pages to questions, assign to an examiner; examiner sees only `anon_code` | L |
| **4 OCR** (O1–O4, N1–N2) | `OCRProvider` + Vision adapter, preprocessing, confidence rules, batch job runner, processing-status | Processing screen with polling; answer list; workspace shell (image + OCR panel + banner + correction) | Run OCR on sample scans; low-confidence answers show the verification banner; text edits persist | L |
| **5 Standard AI evaluation + marking** (V1–V3, M1–M2) | Prompt v1, `LLMClient`, evaluator, validator, repair retry, marking service with guards | AI panel, confidence badge, marking panel (accept/modify/manual), navigation to next | **Core slice works end to end**: OCR → AI suggestion → examiner accepts/modifies → `final_marks` set. Works with Pinecone unset | L |
| **6 Reference-grounded mode** (D1–D3, D5) | Embeddings adapter, Pinecone store, indexer, retriever, fallback logic | Reference documents screen, retrieval test box, mode badge in the AI panel | A `reference_grounded` question shows retrieved-source-aware reasoning; a `standard` question makes no Pinecone call; empty retrieval falls back with a warning | M |
| **7 Anomalies + unchecked detection** (AN1–AN3) | 6 detectors, runner, dedupe, auto-run on entering `moderation` | Flags on dashboards, anomaly list and filters | Seeded data produces expected flags; re-run does not duplicate | M |
| **8 Moderation** (MD1–MD2) | Queue, decision service, anomaly resolution | Moderator dashboard, moderation view | Override with reason changes `final_marks`; anomaly becomes `resolved` | M |
| **9 Results + analytics** (RS1–RS4, AL1–AL4) | Result service, analytics aggregates | Analytics page with charts, results dashboard, examiner dashboard progress | Publish results for the seeded exam; charts match the database | M |
| **10 Polish + demo** | `seed_demo.py` (fake OCR/AI fallbacks), error handling pass, deploy backend, README updates | Mobile pass on the workspace, empty/error states, deploy frontend, Playwright smoke test | Full demo script (section 4) runs on the deployed URLs | M |
| **11 SHOULD HAVE** (as time allows) | AL5–AL6, S3, RS5, D4, extra detectors, auto mapping suggestion | Summary panel, import UI, export button, shortcuts | Each item tickable independently | – |

Frontend can run ahead of the backend by one phase using mocks. **Freeze rule:** when Claude changes an endpoint, `api-spec.md` is updated first and `openapi.json` re-exported. Gemini regenerates types.

## 3. Progress checklist (tick at the end of each session)

- [x] 0.1 Backend skeleton + DB + Alembic
- [x] 0.2 Models + first migration
- [x] 0.3 Frontend skeleton + mock layer + type generation
- [x] 1.1 Auth/RBAC backend
- [x] 1.2 Login + guards + users UI
- [x] 2.1 Exams/questions/rubrics backend
- [x] 2.2 Exam + rubric editor UI
- [x] 3.1 Storage + upload + mapping + assignment backend
- [x] 3.2 Upload + mapping + assignment UI
- [x] 4.1 OCR adapter + preprocessing + confidence + job runner
- [x] 4.2 Processing screen + answer list + OCR panel
- [x] 5.1 Evaluator + validator + LLM client
- [x] 5.2 Marking service + guards
- [x] 5.3 Workspace AI panel + marking panel
- [x] 6.1 Pinecone indexer + retriever + fallback
- [x] 6.2 Reference documents UI
- [x] 7.1 Anomaly detectors + runner
- [x] 7.2 Anomaly UI
- [x] 8.1 Moderation backend
- [x] 8.2 Moderator UI
- [x] 9.1 Results + analytics backend
- [x] 9.2 Analytics + results UI
- [x] 10.1 Seed/demo data
- [x] 10.2 Deploy + mobile pass + smoke test

**Next session should start with: step 7.1 — Anomaly detectors + runner (backend), per `ai-pipeline.md` §10.**
Step 6.2 (reference documents UI) is a frontend step (Gemini); the backend endpoints it needs (D1, D2, D3, D5) are
done and in `backend/openapi.json` — D4 (reindex) is SHOULD HAVE and intentionally not built. Before 7.1, note these
open items carried forward:

- **V2 (batch AI evaluation, `POST /exams/{id}/ai-evaluation/run`) is still not built.** Not covered by 5.1, 5.2, or
  6.1. Decide with the owner where it goes — likely alongside 7.1's runner, since both are background-job patterns.
- **`app/core/storage/`** — present in this ZIP; confirm the `.gitignore` fix mentioned in the previous note was
  actually applied and committed (anchored `/storage/` / `/backend/storage/`), not just worked around locally.
- **Frontend contract mismatch for 5.3** (`MarkingPanel.tsx` criterion_marks shape) — still open, still frontend-side.
- **NEW — Pinecone REST contract is UNVERIFIED against a live instance.** `app/ai/rag/pinecone_store.py` was written
  with no internet access; the control-plane/data-plane request shapes match Pinecone's documented API as of this
  codebase's training data but were never exercised against the real service. It fails safe (falls back to standard
  mode via `REFERENCE_UNAVAILABLE`) if the contract is wrong, so nothing breaks — but reference-grounded mode won't
  produce real retrieval until someone with real `PINECONE_API_KEY`/`OPENAI_API_KEY` credentials and internet access
  verifies it end to end. See the docstring at the top of `pinecone_store.py` for exactly what to check.
- **NEW — one new dependency added:** `python-docx` (for DOCX reference-document text extraction). Everything else
  in 6.1 (OpenAI embeddings, Pinecone) goes through `httpx` directly, matching the existing LLM-client pattern —
  no SDK added for either.
- **NEW — new env vars:** `OPENAI_API_KEY` was added to `.env.example` and `app/core/config.py` (was missing before;
  `EMBEDDING_PROVIDER`/`EMBEDDING_MODEL`/`PINECONE_*` already existed but had no key to actually call OpenAI).


## 4. Demo script (target for phase 10)

1. Admin logs in, opens the seeded exam with three questions (two standard, one reference-grounded), and shows a rubric and an uploaded reference document.
2. Admin runs OCR and AI evaluation and watches the counters move.
3. Examiner opens the workspace. A low-confidence answer shows the verification banner. The examiner corrects the text, re-runs AI, then accepts. Another answer is modified, another marked manually.
4. Admin moves the exam to moderation. Anomalies appear (one unchecked answer, one AI-disagreement, one examiner deviation).
5. Moderator opens a flagged answer, compares marks and AI reasoning, and overrides with a reason.
6. Admin computes and publishes results. The analytics page shows distributions and examiner comparison. (Optional: AI summary.)
7. Show the same flow on a phone-size window for the examiner workspace.

## 5. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Handwriting OCR poor on demo scans | Prepare clean sample scans in advance; seed script includes stored OCR outputs; keep the correction step in the demo as a feature |
| LLM latency or rate limits | Batch concurrency 4; pre-run AI on demo data; sync single-answer fallback |
| Two agents diverge on the contract | Contract-first rule; generated types; only Claude edits `api-spec.md` |
| Scope creep | Anti-overengineering test; cut order in section 1 |
| Ephemeral disk on free hosts | Use a bucket for the deployed demo (D-13) |
| Session limits | One step per session; read only `instruction.md` + one doc; update the checklist before ending |
