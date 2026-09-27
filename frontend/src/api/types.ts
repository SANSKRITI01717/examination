import type {
  UserRole,
  ExamStatus,
  EvaluationMode,
  SheetStatus,
  OcrStatus,
  AiStatus,
  MarkingStatus,
  FinalSource,
  EvaluationSource,
  EvaluationStatus,
  DocType,
  DocStatus,
  AnomalyType,
  AnomalySeverity,
  AnomalyStatus,
  ModerationDecision,
  ResultStatus,
} from '../lib/constants'

export type {
  UserRole,
  ExamStatus,
  EvaluationMode,
  SheetStatus,
  OcrStatus,
  AiStatus,
  MarkingStatus,
  FinalSource,
  EvaluationSource,
  EvaluationStatus,
  DocType,
  DocStatus,
  AnomalyType,
  AnomalySeverity,
  AnomalyStatus,
  ModerationDecision,
  ResultStatus,
}



export interface User {
  id: number
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface ExamSettings {
  ocr_low_conf_threshold?: number
  ai_low_conf_threshold?: number
  ai_disagreement_ratio?: number
  too_fast_seconds?: number
  z_threshold?: number
  min_sample_size?: number
  retrieval_top_k?: number
  retrieval_min_score?: number
  [key: string]: any
}

export interface Exam {
  id: number
  title: string
  course_code: string
  exam_date: string | null
  status: ExamStatus
  settings: ExamSettings
  created_at: string
}

export interface ExamDetail extends Exam {
  question_count: number
  sheet_count: number
  answer_count: number
}

export interface RubricCriterion {
  id: string
  name: string
  max_marks: number
  description?: string
}

export interface Rubric {
  question_id: number
  criteria: RubricCriterion[]
  guidance?: string | null
}

export interface Question {
  id: number
  exam_id: number
  question_number: string
  text: string
  max_marks: number
  evaluation_mode: EvaluationMode
  display_order: number
  rubric?: Rubric
}

export interface Student {
  id: number
  roll_number: string
  full_name: string
  department?: string | null
  created_at?: string
}

export interface AnswerSheet {
  id: number
  exam_id: number
  student_id?: number
  anon_code: string
  status: SheetStatus
  page_count: number
  created_at: string
  student?: Student
  mapped?: boolean
  answers_total?: number
  answers_marked?: number
}

export interface AnswerSheetPage {
  id: number
  sheet_id: number
  page_number: number
  image_url: string
}

export interface AnswerSummary {
  id: number
  question_id: number
  question_number: string
  is_attempted: boolean
  page_start: number
  page_end: number
  marking_status: MarkingStatus
  final_marks: number | null
}

export interface AnswerSheetDetail extends AnswerSheet {
  pages: AnswerSheetPage[]
  answers: AnswerSummary[]
}

export interface AnswerRow {
  id: number
  anon_code: string
  question_number: string
  marking_status: MarkingStatus
  ocr_status: OcrStatus
  ai_status: AiStatus
  ocr_review_required: boolean
  final_marks: number | null
  max_marks: number
}

export interface AiCriterionResult {
  criterion_id: string
  criterion: string
  max_marks: number
  awarded_marks: number
  reason: string
}

export interface AiEvaluation {
  id: number
  answer_id: number
  mode_requested: EvaluationMode
  mode_used: EvaluationMode
  model_name: string
  prompt_version: string
  suggested_marks: number
  max_marks: number
  confidence: number
  llm_confidence: number
  criteria: AiCriterionResult[]
  overall_reason: string
  retrieval?: any
  warnings: string[]
  stale: boolean
  created_at: string
}

export interface Evaluation {
  id: number
  marks_awarded: number
  criterion_marks?: Record<string, number>
  comment?: string
  source: EvaluationSource
  status: EvaluationStatus
  submitted_at: string
  examiner: { id: number; full_name: string }
}

export interface Moderation {
  id: number
  answer_id: number
  decision: ModerationDecision
  moderated_marks: number
  reason?: string
  moderator: { id: number; full_name: string }
  created_at: string
}

export interface Anomaly {
  id: number
  exam_id: number
  type: AnomalyType
  severity: AnomalySeverity
  answer_id: number
  question_id: number
  examiner_id?: number
  score?: number
  details: Record<string, any>
  status: AnomalyStatus
  note?: string
  detected_at: string
}

export interface AnswerDetail {
  id: number
  exam_id: number
  anon_code: string
  question: {
    id: number
    question_number: string
    text: string
    max_marks: number
    evaluation_mode: EvaluationMode
  }
  rubric: Rubric
  pages: { id: number; page_number: number; image_url: string }[]
  is_attempted: boolean
  ocr: {
    status: OcrStatus
    text: string
    verified_text: string | null
    confidence: number | null
    review_required: boolean
    verified: boolean
  }
  ai: {
    status: AiStatus
    latest: AiEvaluation | null
  }
  evaluation: Evaluation | null
  marking_status: MarkingStatus
  final_marks: number | null
  final_source: FinalSource | null
  anomalies?: Anomaly[]
  moderation?: Moderation | null
  navigation: {
    position: number
    total: number
    prev_answer_id: number | null
    next_answer_id: number | null
  }
  student?: Student
}

export interface ReferenceDoc {
  id: number
  exam_id: number
  question_id?: number | null
  title: string
  doc_type: DocType
  status: DocStatus
  chunk_count: number
  error?: string | null
  created_at: string
}

export interface ProcessingStatus {
  ocr: { pending: number; processing: number; done: number; failed: number }
  ai: { not_requested: number; pending: number; processing: number; done: number; failed: number }
  review_required: number
  marking: { pending: number; marked: number; flagged: number; moderated: number }
}

export interface AnalyticsOverview {
  answers_total: number
  ocr_done: number
  ai_done: number
  marked: number
  flagged: number
  moderated: number
  unchecked: number
  low_ocr_confidence: number
  avg_seconds_per_answer: number
}

export interface ExaminerAnalytics {
  examiner: { id: number; full_name: string }
  marked: number
  mean: number
  sd: number
  mean_vs_global: number
  avg_seconds: number
  pct_ai_accepted: number
  pct_ai_modified: number
  pct_manual: number
  flags: number
}

export interface QuestionAnalytics {
  question_id: number
  question_number: string
  mean: number
  sd: number
  min: number
  max: number
  histogram: { bucket: string; count: number }[]
}

export interface ExaminerProgress {
  assigned: number
  marked: number
  remaining: number
  review_required: number
  avg_seconds: number
}

export interface ModerationQueueItem {
  answer_id: number
  anon_code: string
  question_number: string
  examiner: { id: number; full_name: string }
  marks: number
  ai_suggested_marks: number | null
  anomalies: { type: AnomalyType; severity: AnomalySeverity }[]
}

export interface ExamResultItem {
  id: number
  student: Student | { anon_code: string }
  total_marks: number
  max_marks: number
  percentage: number
  status: ResultStatus
}

export interface ExamResults {
  items: ExamResultItem[]
  stats: {
    mean: number
    median: number
    pass_rate?: number
    min: number
    max: number
  }
}

export interface ResultDetail {
  result: ExamResultItem
  breakdown: {
    question_number: string
    marks: number
    max_marks: number
    final_source: FinalSource
  }[]
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ApiErrorDetail {
  code: string
  message: string
  details?: any
}

export interface ApiResponseError {
  error: ApiErrorDetail
}
