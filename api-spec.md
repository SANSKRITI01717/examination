# api-spec.md

The contract between backend (Claude) and frontend (Gemini). Backend updates this file **before** changing an endpoint. FastAPI exports `openapi.json` from the implementation. This document defines intent and business rules.

## 1. Conventions

- Base path `/api/v1`. JSON UTF-8. Auth header: `Authorization: Bearer <jwt>`.
- Roles: `A` admin, `E` examiner, `M` moderator. `E*` = examiner, and only for answers assigned to them.
- Tags: **(SH)** = SHOULD HAVE. All other endpoints are MVP.
- Pagination: `?page=1&page_size=25` → `{ "items": [...], "total": 132, "page": 1, "page_size": 25 }`.
- IDs are integers. Timestamps are ISO-8601 UTC. Marks are numbers (0.5 steps).
- **Standard error body** (`4xx/5xx`): `{ "error": { "code": "EXAM_LOCKED", "message": "...", "details": {} } }`
- **Errors that apply to every endpoint** (not repeated in tables): `401 UNAUTHENTICATED`, `403 FORBIDDEN` (wrong role or not assigned), `404 NOT_FOUND`, `422 VALIDATION_ERROR`.
- Examiner and moderator responses never contain `student` data. Only `anon_code`.
- Long-running batch endpoints return `202 { "queued": n }` and are observed through `GET /exams/{id}/processing-status`.

## 2. Authentication

| ID | Method Path | Purpose | Auth | Request | Response | Specific errors |
|---|---|---|---|---|---|---|
| A1 | POST `/auth/login` | Log in | public | `{email, password}` | `{access_token, token_type:"bearer", expires_in, user:{id,email,full_name,role}}` | 401 `INVALID_CREDENTIALS`, 403 `USER_INACTIVE` |
| A2 | GET `/auth/me` | Current user | any | – | `user` | – |

## 3. Users

| ID | Method Path | Purpose | Auth | Request | Response | Specific errors |
|---|---|---|---|---|---|---|
| U1 | POST `/users` | Create account | A | `{email, full_name, role, password}` | `user` | 409 `EMAIL_EXISTS` |
| U2 | GET `/users` | List users (`?role&is_active&page`) | A | – | paginated `user` | – |
| U3 | PATCH `/users/{id}` | Edit / deactivate | A | `{full_name?, role?, is_active?, password?}` | `user` | 409 `CANNOT_DEACTIVATE_SELF` |

## 4. Exams

| ID | Method Path | Purpose | Auth | Request | Response | Specific errors |
|---|---|---|---|---|---|---|
| E1 | POST `/exams` | Create exam | A | `{title, course_code, exam_date?, settings?}` | `exam` | – |
| E2 | GET `/exams` | List exams. A and M: all. E: exams with assigned answers | any | – | `exam[]` | – |
| E3 | GET `/exams/{id}` | Exam + counts | any | – | `exam + {question_count, sheet_count, answer_count}` | – |
| E4 | PATCH `/exams/{id}` | Edit title, date, settings | A | `{title?, course_code?, exam_date?, settings?}` | `exam` | 422 `INVALID_SETTINGS` |
| E5 | POST `/exams/{id}/transition` | Move lifecycle state | A | `{to: "evaluation"|"moderation"|"completed"}` | `exam` | 409 `INVALID_TRANSITION`, 409 `PRECONDITION_FAILED` (`details.failures[]`) |

`exam` = `{id, title, course_code, exam_date, status, settings, created_at}`.

## 5. Questions and rubrics

| ID | Method Path | Purpose | Auth | Request | Response | Specific errors |
|---|---|---|---|---|---|---|
| Q1 | POST `/exams/{id}/questions` | Add question | A | `{question_number, text, max_marks, evaluation_mode?="standard"}` | `question` | 409 `EXAM_LOCKED`, 409 `DUPLICATE_QUESTION_NUMBER` |
| Q2 | GET `/exams/{id}/questions` | List questions (with rubric) | any | – | `question[]` | – |
| Q3 | PATCH `/questions/{id}` | Edit question (incl. `evaluation_mode`) | A | partial `question` | `question` | 409 `EXAM_LOCKED` |
| Q4 | DELETE `/questions/{id}` | Delete (draft exams only) | A | – | `204` | 409 `EXAM_LOCKED`, 409 `HAS_ANSWERS` |
| R1 | PUT `/questions/{id}/rubric` | Create or replace rubric | A | `{criteria:[{id,name,max_marks,description?}], guidance?}` | `rubric` | 422 `RUBRIC_SUM_MISMATCH`, 422 `DUPLICATE_CRITERION_ID`, 409 `EXAM_LOCKED` |
| R2 | GET `/questions/{id}/rubric` | Read rubric | any | – | `rubric` | – |

`question` = `{id, exam_id, question_number, text, max_marks, evaluation_mode, display_order, rubric?}`
`rubric` = `{question_id, criteria:[{id,name,max_marks,description}], guidance}`

## 6. Students

| ID | Method Path | Purpose | Auth | Request | Response | Specific errors |
|---|---|---|---|---|---|---|
| S1 | POST `/students` | Add student | A | `{roll_number, full_name, department?}` | `student` | 409 `ROLL_EXISTS` |
| S2 | GET `/students` | Search (`?q&page`) | A | – | paginated `student` | – |
| S3 (SH) | POST `/students/import` | CSV import | A | multipart `file` (`roll_number,full_name,department`) | `{created, skipped, errors[]}` | 415 `UNSUPPORTED_FILE` |

## 7. Answer sheets, page mapping, assignment

| ID | Method Path | Purpose | Auth | Request | Response | Specific errors |
|---|---|---|---|---|---|---|
| AS1 | POST `/exams/{id}/answer-sheets` | Upload one student's script (JPEG/PNG pages **or** one PDF). PDF is split into page images server-side. `anon_code` auto-generated | A | multipart `student_id`, `files[]` | `sheet` (status `uploaded`) | 409 `SHEET_EXISTS`, 409 `EXAM_LOCKED`, 415 `UNSUPPORTED_FILE`, 413 `FILE_TOO_LARGE` |
| AS2 | GET `/exams/{id}/answer-sheets` | List sheets with progress (`?status&page`) | A | – | paginated `sheet` + `{student, mapped, answers_total, answers_marked}` | – |
| AS3 | GET `/answer-sheets/{id}` | Sheet, pages and answer summaries. E sees only assigned answers | A, E*, M | – | `sheet + pages[] + answers[]` | – |
| AS4 | PUT `/answer-sheets/{id}/mapping` | Map page ranges to questions; creates or updates answer rows. Sets sheet `mapped` | A | `{items:[{question_id, page_start, page_end, is_attempted}]}` | `answers[]` | 422 `PAGE_RANGE_INVALID`, 409 `ANSWER_ALREADY_MARKED`, 409 `EXAM_LOCKED` |
| AS5 | GET `/pages/{page_id}/image` | Stream a page image (authorised) | A, E*, M | – | `image/jpeg` binary | – |
| AS6 | POST `/exams/{id}/assignments` | Assign unmarked answers to examiners | A | `{examiner_ids:[..], strategy:"by_sheet"|"by_question"}` | `{assigned, per_examiner:{"12":40}}` | 422 `NOT_AN_EXAMINER`, 409 `NO_MAPPED_SHEETS` |

`sheet` = `{id, exam_id, anon_code, status, page_count, created_at}`. `student` appears only for admin.

Default mapping helper for the UI: if `page_count == question_count`, pre-fill "one page per question".

## 8. OCR

| ID | Method Path | Purpose | Auth | Request | Response | Specific errors |
|---|---|---|---|---|---|---|
| O1 | POST `/exams/{id}/ocr/run` | Batch OCR. Default: all `pending`/`failed` attempted answers | A | `{answer_ids?: []}` | `202 {queued}` | 409 `NO_MAPPED_SHEETS` |
| O2 | POST `/answers/{id}/ocr` | Re-run OCR for one answer | A, E* | – | `202 {queued:1}` | 409 `ANSWER_LOCKED` |
| O3 | PATCH `/answers/{id}/text` | Correct OCR text and/or mark it verified | E* | `{verified_text?, ocr_verified: true}` | `answer.ocr` (see N2) | 409 `ANSWER_LOCKED`, 422 `EMPTY_TEXT` |
| O4 | GET `/exams/{id}/processing-status` | Progress counters (polled) | A, M | – | `{ocr:{pending,processing,done,failed}, ai:{not_requested,pending,processing,done,failed}, review_required, marking:{pending,marked,flagged,moderated}}` | – |

`ANSWER_LOCKED` = the exam is not in `evaluation`, or (for non-admins) the answer is already `moderated`.

## 9. Answers and the examiner workspace

| ID | Method Path | Purpose | Auth | Request | Response | Specific errors |
|---|---|---|---|---|---|---|
| N1 | GET `/answers` | Filterable list: `exam_id` (required), `sheet_id`, `question_id`, `marking_status`, `assigned_to=me`, `ocr_review_required`, `page` | A, E*, M | – | paginated `answer_row` | – |
| N2 | GET `/answers/{id}` | **Full workspace payload** (below). First call by an examiner sets `evaluations.opened_at` | A, E*, M | – | `answer_detail` | – |

`answer_row` = `{id, anon_code, question_number, marking_status, ocr_status, ai_status, ocr_review_required, final_marks, max_marks}`

**`answer_detail` (N2) example**

```json
{
  "id": 812, "exam_id": 3, "anon_code": "S-0417",
  "question": {"id": 21, "question_number": "3", "text": "Explain the TCP three-way handshake.",
               "max_marks": 10, "evaluation_mode": "standard"},
  "rubric": {"criteria": [
      {"id": "c1", "name": "SYN", "max_marks": 2, "description": "Client sends SYN with initial sequence number"},
      {"id": "c2", "name": "SYN-ACK", "max_marks": 2, "description": "..."},
      {"id": "c3", "name": "ACK", "max_marks": 2, "description": "..."},
      {"id": "c4", "name": "Purpose", "max_marks": 2, "description": "..."},
      {"id": "c5", "name": "Overall correctness", "max_marks": 2, "description": "..."}],
    "guidance": "Accept alternative wording."},
  "pages": [{"id": 55, "page_number": 2, "image_url": "/api/v1/pages/55/image"}],
  "is_attempted": true,
  "ocr": {"status": "done", "text": "First the client sends SYN...", "verified_text": null,
          "confidence": 0.74, "review_required": true, "verified": false},
  "ai": {"status": "done", "latest": {
      "id": 940, "mode_used": "standard", "suggested_marks": 7, "max_marks": 10,
      "confidence": 0.74, "llm_confidence": 0.86,
      "criteria": [{"criterion_id": "c1", "criterion": "SYN", "max_marks": 2, "awarded_marks": 2, "reason": "States that the client sends SYN."}],
      "overall_reason": "Covers SYN and SYN-ACK; ACK step and purpose are missing.",
      "warnings": ["LOW_OCR_CONFIDENCE"], "stale": false, "created_at": "2026-09-19T09:30:00Z"}},
  "evaluation": null,
  "marking_status": "pending", "final_marks": null, "final_source": null,
  "anomalies": [],
  "moderation": null,
  "navigation": {"position": 3, "total": 12, "prev_answer_id": 811, "next_answer_id": 813}
}
```

Role differences: `anomalies` and `moderation` are returned to M and A only. `student:{roll_number, full_name}` is added for A only. `evaluation` (when present) = `{id, marks_awarded, criterion_marks, comment, source, status, submitted_at, examiner:{id,full_name}}`. Navigation follows the caller's own filtered list (examiner: their assigned answers).

## 10. AI evaluation

| ID | Method Path | Purpose | Auth | Request | Response | Specific errors |
|---|---|---|---|---|---|---|
| V1 | POST `/answers/{id}/ai-evaluation` | Run AI for one answer (synchronous, ≈5–20 s). Mode comes from the question | A, E* | `{force_standard?: false}` | `ai_evaluation` | 409 `NO_TEXT_TO_EVALUATE`, 409 `RUBRIC_MISSING`, 409 `ANSWER_LOCKED`, 422 `AI_OUTPUT_INVALID` (after one repair retry), 502 `LLM_UNAVAILABLE` |
| V2 | POST `/exams/{id}/ai-evaluation/run` | Batch AI on answers with `ocr_status=done` and no current suggestion | A | `{answer_ids?: [], only_pending?: true}` | `202 {queued}` | 409 `NO_OCR_TEXT` |
| V3 | GET `/answers/{id}/ai-evaluations` | History of AI suggestions | A, E*, M | – | `ai_evaluation[]` | – |

`force_standard` lets an examiner skip retrieval for a reference-grounded question. It is logged as `mode_requested = standard`.

`ai_evaluation` = `{id, answer_id, mode_requested, mode_used, model_name, prompt_version, suggested_marks, max_marks, confidence, llm_confidence, criteria[], overall_reason, retrieval?, warnings[], stale, created_at}`. `retrieval` is returned to A and M only.

## 11. Reference documents and RAG retrieval (optional layer)

| ID | Method Path | Purpose | Auth | Request | Response | Specific errors |
|---|---|---|---|---|---|---|
| D1 | POST `/exams/{id}/reference-documents` | Upload reference file; chunk, embed and upsert to Pinecone in the background | A | multipart `file`, `title`, `doc_type`, `question_id?` | `doc` (status `uploaded`→`indexing`→`indexed`) | 415 `UNSUPPORTED_FILE` (PDF/DOCX/TXT), 413 `FILE_TOO_LARGE`, 409 `EXAM_LOCKED` |
| D2 | GET `/exams/{id}/reference-documents` | List with status and chunk count | A | – | `doc[]` | – |
| D3 | DELETE `/reference-documents/{id}` | Delete file, DB row and vectors | A | – | `204` | 409 `IN_USE` (a reference_grounded question depends on it and the exam is past `draft`) |
| D4 (SH) | POST `/reference-documents/{id}/reindex` | Re-chunk and re-embed | A | – | `202` | – |
| D5 | POST `/exams/{id}/reference-search` | Test retrieval (debug/preview tool) | A | `{query, question_id?, top_k?=4}` | `{chunks:[{doc_id, title, chunk_index, score, text}]}` | 409 `NO_INDEXED_DOCUMENTS`, 503 `VECTOR_STORE_UNAVAILABLE` |

`doc` = `{id, exam_id, question_id, title, doc_type, status, chunk_count, error, created_at}`.
Retrieval during evaluation is internal to V1/V2 and is **not** exposed to examiners.

## 12. Marks (examiner decisions)

| ID | Method Path | Purpose | Auth | Request | Response | Specific errors |
|---|---|---|---|---|---|---|
| M1 | POST `/answers/{id}/evaluation/accept-ai` | Accept the AI suggestion as-is (creates a submitted evaluation, `source = ai_accepted`) | E* | `{ai_evaluation_id, active_seconds}` | `evaluation` | 409 `OCR_NOT_VERIFIED`, 409 `AI_EVAL_STALE`, 409 `ANSWER_LOCKED` |
| M2 | PUT `/answers/{id}/evaluation` | Save draft or submit explicit marks (`ai_modified` or `manual`) | E* | `{marks_awarded, criterion_marks?, comment?, source, ai_evaluation_id?, active_seconds, submit}` | `evaluation` | 422 `MARKS_OUT_OF_RANGE`, 422 `CRITERIA_SUM_MISMATCH`, 409 `ANSWER_LOCKED` |

Rules: submitting sets `answers.final_marks = marks_awarded`, `final_source = examiner`, `marking_status = marked` (or stays `flagged` if an open anomaly exists). `source = ai_modified` requires `ai_evaluation_id`. Re-submission is allowed while the exam is in `evaluation`.

**Implementation notes (step 5.2 — behaviour the rules above leave open)**

- `active_seconds` (M1, M2) and `submit` (M2) are required. `comment`, `criterion_marks`, `ai_evaluation_id` are optional.
- `criterion_marks` is a **list** `[{"criterion_id": "c1", "awarded_marks": 2}]`, matching `database-schema.md` (not an `{id: marks}` map). Each id must exist in the rubric, appear once, and be `0..criterion.max_marks`. Their sum must equal `marks_awarded` (`422 CRITERIA_SUM_MISMATCH`). M1 stores the AI suggestion's per-criterion marks the same way.
- Marks (total and per criterion) must be in 0.5 steps. Out of range → `422 MARKS_OUT_OF_RANGE`; wrong step, unknown/duplicate criterion, or `ai_modified` without `ai_evaluation_id` → `422 VALIDATION_ERROR`. `source` accepts only `ai_modified` or `manual`; `ai_accepted` is reachable only through M1.
- `ai_evaluation_id` must belong to the same answer, otherwise `404 NOT_FOUND`.
- Only the assigned examiner may call M1/M2 (admin and moderator get `403`). Both need the exam in `evaluation` and the answer not `moderated`, otherwise `409 ANSWER_LOCKED`.
- M2 with `submit=false` saves a draft and never touches `answers.final_marks`. Once an evaluation is `submitted`, a further `submit=false` call returns `409 ANSWER_LOCKED` (`details.reason = ALREADY_SUBMITTED`); change submitted marks by calling M2/M1 again with the new values and `submit=true`.
- Both use the single evaluation row per answer; the placeholder draft that N2 creates on first open is reused.
- M1 guard order: 404 → 403 → `ANSWER_LOCKED` → 404 (foreign `ai_evaluation_id`) → `OCR_NOT_VERIFIED` → `AI_EVAL_STALE`. `OCR_NOT_VERIFIED` applies to M1 only (invariant 8); `ai_modified` and `manual` stay available while OCR is unverified.

## 13. Moderation

| ID | Method Path | Purpose | Auth | Request | Response | Specific errors |
|---|---|---|---|---|---|---|
| MD1 | GET `/exams/{id}/moderation/queue` | Flagged answers with anomaly summaries, highest severity first (`?anomaly_type&examiner_id&page`) | M, A | – | paginated `{answer_id, anon_code, question_number, examiner:{id,full_name}, marks, ai_suggested_marks, anomalies:[{type,severity}]}` | – |
| MD2 | POST `/answers/{id}/moderation` | Confirm or override the examiner's marks. Resolves the answer's open anomalies. The moderator inspects the answer through N2 | M | `{decision:"confirmed"|"overridden", moderated_marks, reason?}` | `moderation` | 422 `REASON_REQUIRED`, 422 `MARKS_OUT_OF_RANGE`, 409 `NOT_MARKED`, 409 `EXAM_NOT_IN_MODERATION` |

`confirmed` requires `moderated_marks` equal to the examiner's marks. Both write `answers.final_marks`, `final_source = moderator`, `marking_status = moderated`.

## 14. Anomalies

| ID | Method Path | Purpose | Auth | Request | Response | Specific errors |
|---|---|---|---|---|---|---|
| AN1 | POST `/exams/{id}/anomalies/detect` | Run detectors (idempotent via `dedupe_key`). Also runs on transition to `moderation` | A, M | `{detectors?: [type]}` | `{created, updated, by_type:{}}` | 409 `NOT_ENOUGH_DATA` (only when every detector was skipped) |
| AN2 | GET `/exams/{id}/anomalies` | List (`?type&severity&status&examiner_id&question_id&page`) | A, M | – | paginated `anomaly` | – |
| AN3 | PATCH `/anomalies/{id}` | Dismiss or reopen with a note. `resolved` is set only by moderation | A, M | `{status:"dismissed"|"open", note?}` | `anomaly` | 409 `ALREADY_RESOLVED` |

`anomaly` = `{id, exam_id, type, severity, answer_id, question_id, examiner_id, score, details, status, note, detected_at}`.

## 15. Analytics and summaries

| ID | Method Path | Purpose | Auth | Request | Response | Specific errors |
|---|---|---|---|---|---|---|
| AL1 | GET `/exams/{id}/analytics/overview` | Progress counters and completion % | A, M | – | `{answers_total, ocr_done, ai_done, marked, flagged, moderated, unchecked, low_ocr_confidence, avg_seconds_per_answer}` | – |
| AL2 | GET `/exams/{id}/analytics/examiners` | Per-examiner statistics | A, M | – | `[{examiner, marked, mean, sd, mean_vs_global, avg_seconds, pct_ai_accepted, pct_ai_modified, pct_manual, flags}]` | – |
| AL3 | GET `/exams/{id}/analytics/questions` | Per-question statistics | A, M | – | `[{question_id, mean, sd, min, max, histogram:[{bucket,count}]}]` | – |
| AL4 | GET `/exams/{id}/analytics/my-progress` | Examiner's own workload | E | – | `{assigned, marked, remaining, review_required, avg_seconds}` | – |
| AL5 (SH) | POST `/exams/{id}/summaries` | Generate an AI narrative from computed statistics | A, M | `{scope:"exam"|"examiner", examiner_id?}` | `summary` | 409 `NOT_ENOUGH_DATA`, 502 `LLM_UNAVAILABLE` |
| AL6 (SH) | GET `/exams/{id}/summaries` | Stored summaries | A, M | – | `summary[]` | – |

`summary` = `{id, scope, examiner_id, content, stats, created_at}`.

## 16. Results

| ID | Method Path | Purpose | Auth | Request | Response | Specific errors |
|---|---|---|---|---|---|---|
| RS1 | POST `/exams/{id}/results/compute` | Compute totals from `final_marks` (recomputable until published) | A | – | `{computed}` | 409 `INCOMPLETE_MARKING` (`details:{pending, open_high_anomalies}`), 409 `EXAM_NOT_READY` (must be `moderation`/`completed`) |
| RS2 | GET `/exams/{id}/results` | List results and summary stats (`?page`) | A, M | – | `{items:[{id,student:{roll_number,full_name},total_marks,max_marks,percentage,status}], stats:{mean,median,pass_rate?,min,max}}` | – |
| RS3 | GET `/results/{id}` | Per-question breakdown | A, M | – | `{result, breakdown:[{question_number, marks, max_marks, final_source}]}` | – |
| RS4 | POST `/exams/{id}/results/publish` | Publish results; exam → `completed` | A | – | `{published}` | 409 `RESULTS_NOT_COMPUTED` |
| RS5 (SH) | GET `/exams/{id}/results/export.csv` | Download CSV | A | – | `text/csv` | – |

M sees `student` as `anon_code` only in RS2/RS3.

## 17. Endpoint count

MVP: 52 endpoints. SHOULD HAVE: 5 (S3, D4, AL5, AL6, RS5). Every endpoint maps to a step in `development-phases.md`.
