# AI-Driven Examination & On-Screen Marking Platform

An AI-assisted platform for university examinations. Admins manage exams, questions and rubrics, and upload scanned answer sheets. OCR digitizes handwriting, an LLM **suggests** marks against the rubric, and the **examiner decides**. The system flags unchecked answers and unusual marking, supports moderation, and produces results and analytics.

> **AI assists. The examiner (and moderator) is always the final decision-maker.**

## Features

| Area | What it does |
|---|---|
| Exam management | Exams, questions, rubrics, lifecycle (draft → evaluation → moderation → completed) |
| Answer sheets | Multi-page upload, page-to-question mapping, examiner assignment, blind marking (anon codes) |
| OCR assistance | Handwriting/print OCR with confidence; low-confidence answers require human verification; examiner can correct text |
| AI evaluation | **Standard** (question + answer + rubric) and **reference-grounded** (adds Pinecone retrieval), chosen per question |
| Examiner workspace | Image + OCR text + rubric + AI suggestion with reasoning and confidence; accept, modify or enter marks |
| Quality control | Unchecked-answer detection, statistical anomaly flags, examiner analytics |
| Moderation | Queue of flagged answers, side-by-side evidence, confirm or override with reason |
| Results | Totals from final marks, publish, dashboards; AI narrative summaries (optional) |
| Mobile | Responsive examiner interface |

## Design principles

- One developer, one backend service, cloud-first. No microservices, queues, Redis or Kubernetes.
- RAG is **optional**. Pinecone stores only reference material, never student answers.
- A rubric is structured data passed to the LLM directly. It is not RAG.
- AI output is validated before it is stored. OCR is treated as assistance, not truth.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, TypeScript, Tailwind CSS, Recharts, TanStack Query |
| Backend | Python, FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL (managed cloud) |
| Auth | JWT + role-based access control |
| AI | LLM API (structured JSON), Google Cloud Vision OCR (replaceable adapter) |
| Optional RAG | Pinecone + cloud embedding API; LangChain text splitter |
| Storage | Local files in dev, S3-compatible bucket when deployed |

## Documentation map

| File | Read it for |
|---|---|
| `instruction.md` | Rules and boundaries for AI coding agents (read first) |
| `architecture.md` | System overview, components, RBAC, flows |
| `database-schema.md` | Tables, enums, invariants |
| `api-spec.md` | Every REST endpoint |
| `ai-pipeline.md` | OCR, evaluation, RAG, anomaly detection explained |
| `backend-plan.md` | Backend structure and services |
| `frontend-plan.md` | Screens, routes, components |
| `development-phases.md` | Build order, checklist, demo script |

## Planned repository layout

```
PROJECT/
├── *.md              # this documentation
├── backend/          # FastAPI app (owner: Claude)
└── frontend/         # React app (owner: Antigravity/Gemini)
```

## Getting started (once code exists)

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill in DATABASE_URL, JWT_SECRET, provider keys
alembic upgrade head
python scripts/seed_demo.py     # demo users, exam, rubrics, sample data
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

Demo logins are created by the seed script (one admin, examiner and moderator).

## Required accounts and keys

PostgreSQL host (Neon or Supabase), an LLM API key, Google Cloud Vision credentials. Optional: Pinecone and an embedding API key for reference-grounded questions. Without Pinecone the system runs fully in standard mode.

## Limitations (be upfront in demos)

- Handwriting recognition is imperfect. Low-confidence answers must be verified by the examiner.
- AI marks are suggestions. Confidence is a review signal, not a guarantee.
- Anomaly flags are statistical hints that ask a human to look, not conclusions.
- Page-to-question mapping is manual in the MVP.

## Scope

**MVP**, **SHOULD HAVE** and **FUTURE** tiers are defined in `development-phases.md` §1.
