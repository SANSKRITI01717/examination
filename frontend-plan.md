# frontend-plan.md

Owner: **Antigravity/Gemini**. Backend contract: `api-spec.md` (endpoint IDs like **E1**, **N2** are referenced below). Project rules: `instruction.md`.

## 1. Stack and rules

- React + Vite + **TypeScript** + Tailwind CSS + Recharts + React Router + TanStack Query (server state and polling).
- API types are **generated from `backend/openapi.json`** (for example with `openapi-typescript`). Never hand-write API types.
- Auth state in a small React context (token in memory + `localStorage`). No global state library.
- Plain Tailwind components (Button, Card, Badge, Table, Modal, Tabs, Toast) in `src/components/ui/`. No large UI kit.
- Image zoom/pan: `react-zoom-pan-pinch` (essential for reading handwriting).
- Mock mode: `VITE_USE_MOCK=true` serves fixtures copied from `api-spec.md` examples so screens can be built before the backend exists.
- Never display student name or roll number outside admin screens. Examiner and moderator screens show `anon_code` only.
- Wherever AI content appears it is labelled **"AI suggestion — you decide"**.

## 2. Folder structure

```
frontend/src/
├── api/            # generated types, fetch client (adds JWT), query hooks per module, mocks/
├── auth/           # AuthProvider, ProtectedRoute(role), useAuth
├── pages/
│   ├── Login.tsx
│   ├── admin/      # AdminDashboard, ExamList, ExamDetail, QuestionEditor, SheetUpload, PageMapping,
│   │               # ReferenceDocs, Assignments, UsersAdmin
│   ├── examiner/   # ExaminerDashboard, AnswerList, Workspace
│   ├── moderator/  # ModeratorDashboard, ModerationView
│   └── shared/     # Analytics, Results
├── components/
│   ├── ui/         # primitives
│   ├── workspace/  # QuestionNav, PageViewer, OcrPanel, RubricPanel, AiSuggestionPanel,
│   │               # CriterionRow, MarkingPanel, ConfidenceBadge, OcrWarningBanner
│   ├── charts/     # Histogram, ExaminerMeanChart, ProgressBar
│   └── layout/     # AppShell, Sidebar (collapses on mobile), PageHeader
└── lib/            # format helpers, constants (enums mirror database-schema.md)
```

## 3. Routes and screens

| Route | Role | Screen | Main content | API |
|---|---|---|---|---|
| `/login` | public | Login | email + password | A1, A2 |
| `/admin` | A | Admin dashboard | exams with status, progress bars, processing status, alerts (unchecked, low-OCR counts) | E2, AL1, O4 |
| `/admin/users` | A | Users | table, create, activate/deactivate | U1–U3 |
| `/admin/exams/new`, `/admin/exams/:id` | A | Exam management | exam form, settings (thresholds), lifecycle stepper with transition button and failure list | E1, E3–E5 |
| `/admin/exams/:id/questions` | A | Question and rubric management | question list; editor with criteria table, live "sum = max marks" check, evaluation mode toggle (Standard / Reference-grounded) | Q1–Q4, R1, R2 |
| `/admin/exams/:id/references` | A | Reference documents | upload, status chips (indexing/indexed/failed), delete, retrieval test box | D1–D3, D5 |
| `/admin/exams/:id/sheets` | A | Sheet upload and list | student picker, drag-and-drop pages, progress per sheet | S1, S2, AS1, AS2 |
| `/admin/sheets/:id/mapping` | A | Page mapping | page thumbnails beside question list; assign page ranges; mark unattempted | AS3, AS4, AS5, Q2 |
| `/admin/exams/:id/assignments` | A | Assign examiners | pick examiners and strategy; shows counts | AS6, U2 |
| `/admin/exams/:id/processing` | A | Processing | buttons "Run OCR", "Run AI evaluation", live counters (polling 10 s) | O1, V2, O4 |
| `/examiner` | E | Examiner dashboard | assigned exams; my progress (marked / remaining / review needed) | E2, AL4 |
| `/examiner/exams/:id/answers` | E | Answer list | filters: status, needs OCR review; open first pending | N1 |
| `/examiner/answers/:id` | E | **Workspace** (section 4) | see below | N2, O2, O3, V1, V3, M1, M2 |
| `/moderator` | M | Moderator dashboard | flagged queue sorted by severity; filters by anomaly type and examiner | MD1, AN2, AN1 |
| `/moderator/answers/:id` | M | Moderation view | workspace layout (read-only) + examiner marks vs AI marks + anomalies + decision form | N2, V3, MD2, AN3 |
| `/exams/:id/analytics` | A, M | Analytics | overview cards, per-question histograms, examiner comparison chart, anomaly counts, AI summary panel (SH) | AL1–AL3, AN2, AL5, AL6 |
| `/exams/:id/results` | A, M | Result dashboard | table, stats, compute and publish buttons, export (SH), row → breakdown drawer | RS1–RS5 |

Route guard: `ProtectedRoute(roles)`. Unauthorised roles are redirected to their own dashboard.

## 4. Examiner workspace (the central screen)

Desktop (≥1024 px), three columns:

```
┌────────────┬──────────────────────────────┬───────────────────────────────┐
│ Question   │ Answer-sheet image           │ Question (text, max marks)    │
│ navigation │ (zoom / pan, page tabs)      │ Rubric criteria               │
│            │                              │ ─────────────────────────────  │
│ Q1 ✔       │                              │ OCR text (editable)           │
│ Q2 ✔       │                              │  ⚠ Human verification needed  │
│ Q3 ●       │                              │  [Confirm text as correct]    │
│ Q4         │                              │ ─────────────────────────────  │
│ Prev / Next│                              │ AI suggestion — you decide    │
│            │                              │  7 / 10   confidence 74% 🟠   │
│            │                              │  criterion rows + reasons     │
│            │                              │ ─────────────────────────────  │
│            │                              │ [Accept] [Modify] [Enter manually] │
│            │                              │ marks input · comment · Submit│
└────────────┴──────────────────────────────┴───────────────────────────────┘
```

Mobile (<768 px): a single column with a bottom tab bar **Image | Text | AI | Marks**. Question navigation becomes a top dropdown. The marks bar stays sticky at the bottom.

**Behaviour**

1. **Load (N2).** Show skeletons. The response drives all panels.
2. **OCR panel.** Editable textarea. Saving calls O3. If `review_required && !verified`, show the banner and disable Accept (tooltip: "Verify the text first"). Modify and manual remain enabled. After a text edit the AI panel shows "Suggestion is out of date — Re-run AI" (V1).
3. **AI panel.** States: not requested (button "Get AI suggestion", V1), loading, done, failed (show error, "Try again", manual marking still available). Show mode badge (Standard / Reference-grounded), criterion rows (awarded/max + reason), `overall_reason`, warnings as chips (`LOW_CONFIDENCE`, `LOW_OCR_CONFIDENCE`, `NO_REFERENCE_FOUND`).
4. **Confidence badge.** ≥0.85 green, 0.70–0.85 amber, <0.70 red plus "Review carefully".
5. **Marking panel.** Accept → M1. Modify → criterion inputs prefilled from AI, total auto-sums, "Submit" → M2 (`source=ai_modified`). Manual → free marks input (0.5 steps, ≤ max) → M2 (`source=manual`). Client validates range before sending. Server errors (`MARKS_OUT_OF_RANGE`, `CRITERIA_SUM_MISMATCH`, `AI_EVAL_STALE`, `OCR_NOT_VERIFIED`) show inline messages.
6. **Time tracking.** Count only while the tab is visible and the user has interacted recently. Send `active_seconds` with M1/M2.
7. **After submit.** Toast, navigate to `navigation.next_answer_id`.
8. **Keyboard (SH).** `A` accept, `N` next, `P` previous, `V` verify text.

The moderation view reuses `PageViewer`, `OcrPanel`, `RubricPanel` and `AiSuggestionPanel` read-only, adds the examiner's marks, the AI marks and the anomaly list, plus a form: decision (confirm / override), marks and a reason (required for override).

## 5. Dashboards (polling, no WebSockets)

| Screen | Poll interval | Source |
|---|---|---|
| Admin processing counters | 10 s | O4 |
| Admin/moderator overview cards | 15 s | AL1 |
| Examiner progress | 30 s | AL4 |
| Moderator queue | 30 s | MD1 |

Polling pauses when the tab is hidden (TanStack Query `refetchIntervalInBackground: false`).

## 6. Charts (Recharts)

- Per-question mark histogram (AL3).
- Examiner mean vs global mean bar chart with sd whiskers (AL2).
- Examiner speed (seconds per answer) and AI acceptance mix (accepted / modified / manual) stacked bar (AL2).
- Overall progress bars (AL1) and anomaly counts by type (AN2).

## 7. Cross-cutting UI rules

- Every list and dashboard has loading, empty and error states.
- Status chips use the enums from `database-schema.md` §3 (colour map in `lib/constants.ts`).
- Anomaly severity: high red, medium amber, low grey. Wording is neutral ("flagged for review"), never accusatory.
- Toasts for success and errors. Show `error.message` from the API body.
- Responsive: admin tables scroll horizontally on small screens; the sidebar collapses to a drawer; the examiner workspace follows section 4.
- Accessibility basics: labels on inputs, focus rings, colour is never the only indicator (badges carry text).

## 8. Testing (UI)

- Component tests (Vitest + Testing Library): `ConfidenceBadge`, `CriterionRow` sum logic, `MarkingPanel` validation, `OcrWarningBanner` gating Accept.
- One Playwright smoke path in mock mode: login as examiner → open workspace → verify OCR → accept AI → next answer.
- Manual mobile check of the workspace at 375 px width.

## 9. Not building

Student portal, notifications centre, theme editor, in-app chat, offline mode, drag-to-annotate on images.
