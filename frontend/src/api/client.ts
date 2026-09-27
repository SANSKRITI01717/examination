import { mockService } from './mocks/mockService'
import type {
  User,
  AuthResponse,
  Exam,
  ExamDetail,
  Question,
  Rubric,
  Student,
  AnswerSheet,
  AnswerSheetDetail,
  AnswerDetail,
  AnswerRow,
  Anomaly,
  ReferenceDoc,
  ProcessingStatus,
  AnalyticsOverview,
  ExaminerAnalytics,
  QuestionAnalytics,
  ExaminerProgress,
  ModerationQueueItem,
  ExamResults,
  ResultDetail,
  AiEvaluation,
} from './types'

// Use mock mode if VITE_USE_MOCK is true or unset (default)
const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'

export const apiClient = {
  isMockMode: USE_MOCK,

  // Auth
  async login(email: string, password?: string): Promise<AuthResponse> {
    if (USE_MOCK) return mockService.login(email)
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) throw await res.json()
    return res.json()
  },

  async getMe(): Promise<User> {
    if (USE_MOCK) return mockService.getMe()
    const token = localStorage.getItem('token')
    const res = await fetch('/api/v1/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) throw await res.json()
    return res.json()
  },

  // Users
  async getUsers(): Promise<{ items: User[]; total: number }> {
    if (USE_MOCK) return mockService.getUsers()
    return fetchWithAuth('/api/v1/users')
  },

  async createUser(data: { email: string; full_name: string; role: 'admin' | 'examiner' | 'moderator'; password?: string }): Promise<User> {
    if (USE_MOCK) return mockService.createUser(data)
    return fetchWithAuth('/api/v1/users', { method: 'POST', body: JSON.stringify(data) })
  },

  async updateUser(id: number, data: Partial<User>): Promise<User> {
    if (USE_MOCK) return mockService.updateUser(id, data)
    return fetchWithAuth(`/api/v1/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
  },

  // Exams
  async getExams(): Promise<Exam[]> {
    if (USE_MOCK) return mockService.getExams()
    return fetchWithAuth('/api/v1/exams')
  },

  async getExam(id: number): Promise<ExamDetail> {
    if (USE_MOCK) return mockService.getExam(id)
    return fetchWithAuth(`/api/v1/exams/${id}`)
  },

  async createExam(data: { title: string; course_code: string; exam_date?: string | null; settings?: any }): Promise<Exam> {
    if (USE_MOCK) return mockService.createExam(data)
    return fetchWithAuth('/api/v1/exams', { method: 'POST', body: JSON.stringify(data) })
  },

  async updateExam(id: number, data: Partial<Exam>): Promise<Exam> {
    if (USE_MOCK) return mockService.updateExam(id, data)
    return fetchWithAuth(`/api/v1/exams/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
  },

  async transitionExam(id: number, to: 'evaluation' | 'moderation' | 'completed'): Promise<Exam> {
    if (USE_MOCK) return mockService.transitionExam(id, to)
    return fetchWithAuth(`/api/v1/exams/${id}/transition`, { method: 'POST', body: JSON.stringify({ to }) })
  },

  // Questions & Rubrics
  async getQuestions(examId: number): Promise<Question[]> {
    if (USE_MOCK) return mockService.getQuestions(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/questions`)
  },

  async createQuestion(examId: number, data: { question_number: string; text: string; max_marks: number; evaluation_mode?: 'standard' | 'reference_grounded' }): Promise<Question> {
    if (USE_MOCK) return mockService.createQuestion(examId, data)
    return fetchWithAuth(`/api/v1/exams/${examId}/questions`, { method: 'POST', body: JSON.stringify(data) })
  },

  async updateQuestion(id: number, data: Partial<Question>): Promise<Question> {
    if (USE_MOCK) return mockService.updateQuestion(id, data)
    return fetchWithAuth(`/api/v1/questions/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
  },

  async deleteQuestion(id: number): Promise<void> {
    if (USE_MOCK) return mockService.deleteQuestion(id)
    return fetchWithAuth(`/api/v1/questions/${id}`, { method: 'DELETE' })
  },

  async saveRubric(questionId: number, data: { criteria: any[]; guidance?: string }): Promise<Rubric> {
    if (USE_MOCK) return mockService.saveRubric(questionId, data)
    return fetchWithAuth(`/api/v1/questions/${questionId}/rubric`, { method: 'PUT', body: JSON.stringify(data) })
  },

  // Students & Sheets
  async getStudents(): Promise<{ items: Student[]; total: number }> {
    if (USE_MOCK) return mockService.getStudents()
    return fetchWithAuth('/api/v1/students')
  },

  async createStudent(data: { roll_number: string; full_name: string; department?: string }): Promise<Student> {
    if (USE_MOCK) return mockService.createStudent(data)
    return fetchWithAuth('/api/v1/students', { method: 'POST', body: JSON.stringify(data) })
  },

  async getSheets(examId: number): Promise<{ items: AnswerSheet[]; total: number }> {
    if (USE_MOCK) return mockService.getSheets(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/answer-sheets`)
  },

  async uploadSheet(examId: number, studentId: number, filesOrCount?: File[] | File | number): Promise<AnswerSheet> {
    if (USE_MOCK) return mockService.uploadSheet(examId, studentId, typeof filesOrCount === 'number' ? filesOrCount : 3)
    const formData = new FormData()
    formData.append('student_id', String(studentId))
    if (Array.isArray(filesOrCount)) {
      filesOrCount.forEach(f => formData.append('files', f))
    } else if (filesOrCount instanceof File) {
      formData.append('files', filesOrCount)
    }
    return fetchWithAuth(`/api/v1/exams/${examId}/answer-sheets`, { method: 'POST', body: formData })
  },

  async getSheetDetail(sheetId: number): Promise<AnswerSheetDetail> {
    if (USE_MOCK) return mockService.getSheetDetail(sheetId)
    return fetchWithAuth(`/api/v1/answer-sheets/${sheetId}`)
  },

  async savePageMapping(sheetId: number, items: { question_id: number; page_start: number; page_end: number; is_attempted: boolean }[]): Promise<any> {
    if (USE_MOCK) return mockService.savePageMapping(sheetId, items)
    return fetchWithAuth(`/api/v1/answer-sheets/${sheetId}/mapping`, { method: 'PUT', body: JSON.stringify({ items }) })
  },

  async assignExaminers(examId: number, examinerIds: number[], strategy: string): Promise<any> {
    if (USE_MOCK) return mockService.assignExaminers(examId, examinerIds, strategy)
    return fetchWithAuth(`/api/v1/exams/${examId}/assignments`, { method: 'POST', body: JSON.stringify({ examiner_ids: examinerIds, strategy }) })
  },

  // Answers & Workspace
  async getAnswers(params: {
    exam_id: number
    sheet_id?: number
    question_id?: number
    marking_status?: string
    assigned_to?: string
    ocr_review_required?: boolean
    page?: number
    page_size?: number
  }): Promise<{ items: AnswerRow[]; total: number; page?: number; page_size?: number }> {
    if (USE_MOCK) return mockService.getAnswers(params)
    const cleanedParams: Record<string, string> = {}
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        cleanedParams[k] = String(v)
      }
    })
    const query = new URLSearchParams(cleanedParams).toString()
    return fetchWithAuth(`/api/v1/answers?${query}`)
  },

  async getAnswerDetail(id: number): Promise<AnswerDetail> {
    if (USE_MOCK) return mockService.getAnswerDetail(id)
    return fetchWithAuth(`/api/v1/answers/${id}`)
  },

  async rerunSingleOcr(id: number): Promise<{ queued: number }> {
    if (USE_MOCK) return mockService.rerunSingleOcr(id)
    return fetchWithAuth(`/api/v1/answers/${id}/ocr`, { method: 'POST' })
  },

  async updateAnswerText(id: number, data: { verified_text?: string; ocr_verified?: boolean }): Promise<any> {
    if (USE_MOCK) return mockService.updateAnswerText(id, data)
    return fetchWithAuth(`/api/v1/answers/${id}/text`, { method: 'PATCH', body: JSON.stringify(data) })
  },

  async runAiEvaluation(id: number, forceStandard?: boolean): Promise<AiEvaluation> {
    if (USE_MOCK) return mockService.runAiEvaluation(id, forceStandard)
    return fetchWithAuth(`/api/v1/answers/${id}/ai-evaluation`, { method: 'POST', body: JSON.stringify({ force_standard: forceStandard }) })
  },

  async acceptAi(id: number, aiEvaluationId: number, activeSeconds: number): Promise<any> {
    if (USE_MOCK) return mockService.acceptAi(id, aiEvaluationId, activeSeconds)
    return fetchWithAuth(`/api/v1/answers/${id}/evaluation/accept-ai`, {
      method: 'POST',
      body: JSON.stringify({ ai_evaluation_id: aiEvaluationId, active_seconds: activeSeconds }),
    })
  },

  async submitEvaluation(
    id: number,
    data: {
      marks_awarded: number
      criterion_marks?: Record<string, number>
      comment?: string
      source: 'ai_modified' | 'manual'
      ai_evaluation_id?: number
      active_seconds: number
      submit: boolean
    }
  ): Promise<any> {
    if (USE_MOCK) return mockService.submitEvaluation(id, data)
    
    // Transform criterion_marks from Record<string, number> to [{criterion_id, awarded_marks}] expected by backend
    const apiData = {
      ...data,
      criterion_marks: data.criterion_marks
        ? Object.entries(data.criterion_marks).map(([criterion_id, awarded_marks]) => ({
            criterion_id,
            awarded_marks,
          }))
        : undefined,
    }
    return fetchWithAuth(`/api/v1/answers/${id}/evaluation`, { method: 'PUT', body: JSON.stringify(apiData) })
  },

  // Reference Documents
  async getDocuments(examId: number): Promise<ReferenceDoc[]> {
    if (USE_MOCK) return mockService.getDocuments(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/reference-documents`)
  },

  async uploadDocument(examId: number, title: string, docType: string, questionId?: number): Promise<ReferenceDoc> {
    if (USE_MOCK) return mockService.uploadDocument(examId, title, docType, questionId)
    return fetchWithAuth(`/api/v1/exams/${examId}/reference-documents`, { method: 'POST', body: JSON.stringify({ title, doc_type: docType, question_id: questionId }) })
  },

  async deleteDocument(id: number): Promise<void> {
    if (USE_MOCK) return mockService.deleteDocument(id)
    return fetchWithAuth(`/api/v1/reference-documents/${id}`, { method: 'DELETE' })
  },

  async searchReference(examId: number, query: string): Promise<{ chunks: any[] }> {
    if (USE_MOCK) return mockService.searchReference(examId, query)
    return fetchWithAuth(`/api/v1/exams/${examId}/reference-search`, { method: 'POST', body: JSON.stringify({ query }) })
  },

  // Moderation
  async getModerationQueue(examId: number): Promise<{ items: ModerationQueueItem[]; total: number }> {
    if (USE_MOCK) return mockService.getModerationQueue(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/moderation/queue`)
  },

  async submitModeration(id: number, data: { decision: 'confirmed' | 'overridden'; moderated_marks: number; reason?: string }): Promise<any> {
    if (USE_MOCK) return mockService.submitModeration(id, data)
    return fetchWithAuth(`/api/v1/answers/${id}/moderation`, { method: 'POST', body: JSON.stringify(data) })
  },

  // Anomalies
  async detectAnomalies(examId: number): Promise<any> {
    if (USE_MOCK) return mockService.detectAnomalies(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/anomalies/detect`, { method: 'POST' })
  },

  async getAnomalies(examId: number): Promise<{ items: Anomaly[]; total: number }> {
    if (USE_MOCK) return mockService.getAnomalies(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/anomalies`)
  },

  async updateAnomaly(id: number, status: 'dismissed' | 'open', note?: string): Promise<Anomaly> {
    if (USE_MOCK) return mockService.updateAnomaly(id, status, note)
    return fetchWithAuth(`/api/v1/anomalies/${id}`, { method: 'PATCH', body: JSON.stringify({ status, note }) })
  },

  // Processing & Polling
  async getProcessingStatus(examId: number): Promise<ProcessingStatus> {
    if (USE_MOCK) return mockService.getProcessingStatus(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/processing-status`)
  },

  async runBatchOcr(examId: number): Promise<{ queued: number }> {
    if (USE_MOCK) return mockService.runBatchOcr(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/ocr/run`, { method: 'POST' })
  },

  async runBatchAi(examId: number): Promise<{ queued: number }> {
    if (USE_MOCK) return mockService.runBatchAi(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/ai-evaluation/run`, { method: 'POST' })
  },

  // Analytics
  async getAnalyticsOverview(examId: number): Promise<AnalyticsOverview> {
    if (USE_MOCK) return mockService.getAnalyticsOverview(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/analytics/overview`)
  },

  async getExaminerAnalytics(examId: number): Promise<ExaminerAnalytics[]> {
    if (USE_MOCK) return mockService.getExaminerAnalytics(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/analytics/examiners`)
  },

  async getQuestionAnalytics(examId: number): Promise<QuestionAnalytics[]> {
    if (USE_MOCK) return mockService.getQuestionAnalytics(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/analytics/questions`)
  },

  async getMyProgress(examId: number): Promise<ExaminerProgress> {
    if (USE_MOCK) return mockService.getMyProgress(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/analytics/my-progress`)
  },

  // Results
  async computeResults(examId: number): Promise<{ computed: boolean }> {
    if (USE_MOCK) return mockService.computeResults(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/results/compute`, { method: 'POST' })
  },

  async getResults(examId: number): Promise<ExamResults> {
    if (USE_MOCK) return mockService.getResults(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/results`)
  },

  async getResultDetail(id: number): Promise<ResultDetail> {
    if (USE_MOCK) return mockService.getResultDetail(id)
    return fetchWithAuth(`/api/v1/results/${id}`)
  },

  async publishResults(examId: number): Promise<{ published: boolean }> {
    if (USE_MOCK) return mockService.publishResults(examId)
    return fetchWithAuth(`/api/v1/exams/${examId}/results/publish`, { method: 'POST' })
  },
}

async function fetchWithAuth(url: string, init?: RequestInit) {
  const token = localStorage.getItem('token')
  const headers = new Headers(init?.headers || {})
  if (!(init?.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  const res = await fetch(url, { ...init, headers })
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ error: { code: 'UNKNOWN_ERROR', message: res.statusText } }))
    throw errorBody
  }
  return res.json()
}
