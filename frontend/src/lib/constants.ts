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

export const EXAM_STATUS_COLORS: Record<ExamStatus, string> = {
  draft: '#9ca3af',
  evaluation: '#3b82f6',
  moderation: '#f59e0b',
  completed: '#22c55e',
}

export const MARKING_STATUS_COLORS: Record<MarkingStatus, string> = {
  pending: '#9ca3af',
  marked: '#22c55e',
  flagged: '#ef4444',
  moderated: '#3b82f6',
}

// Per frontend-plan.md §7: high = red, medium = amber, low = grey.
export const ANOMALY_SEVERITY_COLORS: Record<AnomalySeverity, string> = {
  low: '#9ca3af',
  medium: '#f59e0b',
  high: '#ef4444',
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
