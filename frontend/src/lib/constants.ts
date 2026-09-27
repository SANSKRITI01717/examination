// Enum types mirroring database-schema.md §3. Keep these in sync with the
// backend's enums — they're the single source of truth for status values
// used across the whole frontend.

export type UserRole = 'admin' | 'examiner' | 'moderator'

export type ExamStatus = 'draft' | 'evaluation' | 'moderation' | 'completed'

export type EvaluationMode = 'standard' | 'reference_grounded'

export type SheetStatus = 'uploaded' | 'mapped'

export type OcrStatus = 'pending' | 'processing' | 'done' | 'failed'

export type AiStatus = 'not_requested' | 'pending' | 'processing' | 'done' | 'failed'

export type MarkingStatus = 'pending' | 'marked' | 'flagged' | 'moderated'

export type FinalSource = 'examiner' | 'moderator' | 'system'

export type EvaluationSource = 'ai_accepted' | 'ai_modified' | 'manual'

export type EvaluationStatus = 'draft' | 'submitted'

export type DocType = 'official_answer' | 'guideline' | 'syllabus' | 'other'

export type DocStatus = 'uploaded' | 'indexing' | 'indexed' | 'failed'

export type AnomalyType =
  | 'UNCHECKED_ANSWER'
  | 'MISSING_MARKS'
  | 'QUESTION_OUTLIER'
  | 'EXAMINER_DEVIATION'
  | 'AI_DISAGREEMENT'
  | 'TOO_FAST'
  | 'SCORE_SHIFT'
  | 'REPEATED_PATTERN'
  | 'UNVERIFIED_OCR'

export type AnomalySeverity = 'low' | 'medium' | 'high'

export type AnomalyStatus = 'open' | 'dismissed' | 'resolved'

export type ModerationDecision = 'confirmed' | 'overridden'

export type ResultStatus = 'draft' | 'published'

// UI-facing labels and colour maps.

export const AI_ASSISTANT_LABEL = 'AI suggestion — you decide'

interface StatusStyle {
  bg: string
  text: string
  border: string
}

// Reuses the same Tailwind palette already defined in components/ui/Badge.tsx
// for visual consistency across the app.
export const EXAM_STATUS_COLORS: Record<ExamStatus, StatusStyle> = {
  draft: { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-200' },
  evaluation: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  moderation: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  completed: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
}

export const MARKING_STATUS_COLORS: Record<MarkingStatus, StatusStyle> = {
  pending: { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-200' },
  marked: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  flagged: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
  moderated: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
}

// Per frontend-plan.md §7: high = red, medium = amber, low = grey.
export const ANOMALY_SEVERITY_COLORS: Record<AnomalySeverity, StatusStyle> = {
  low: { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-200' },
  medium: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  high: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
}

// Neutral wording — flags are a reason to look, never an accusation.
export const ANOMALY_TYPE_LABELS: Record<AnomalyType, string> = {
  UNCHECKED_ANSWER: 'Not yet checked',
  MISSING_MARKS: 'Marks missing',
  QUESTION_OUTLIER: 'Unusual mark for this question',
  EXAMINER_DEVIATION: 'Marking pattern differs from peers',
  AI_DISAGREEMENT: 'Marks differ from AI suggestion',
  TOO_FAST: 'Marked very quickly',
  SCORE_SHIFT: 'Recent marking shift',
  REPEATED_PATTERN: 'Repeated identical marks',
  UNVERIFIED_OCR: 'OCR not verified before marking',
}
