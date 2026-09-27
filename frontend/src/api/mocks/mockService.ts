import type {
  User,
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
} from '../types'
import {
  INITIAL_USERS,
  INITIAL_EXAMS,
  INITIAL_QUESTIONS,
  INITIAL_STUDENTS,
  INITIAL_SHEETS,
  INITIAL_DOCUMENTS,
  INITIAL_ANSWERS,
  INITIAL_ANOMALIES,
  INITIAL_PROCESSING_STATUS,
  INITIAL_ANALYTICS_OVERVIEW,
  INITIAL_EXAMINER_ANALYTICS,
  INITIAL_QUESTION_ANALYTICS,
  INITIAL_RESULTS,
  SAMPLE_PAGE_SVG,
} from './fixtures'

const STORAGE_KEY = 'osm_mock_state_v1'

interface MockState {
  users: User[]
  exams: Exam[]
  questions: Question[]
  students: Student[]
  sheets: AnswerSheet[]
  documents: ReferenceDoc[]
  answers: AnswerDetail[]
  anomalies: Anomaly[]
  processingStatus: Record<number, ProcessingStatus>
  results: Record<number, ExamResults>
  currentUser: User | null
}

function loadInitialState(): MockState {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      return JSON.parse(saved)
    }
  } catch (e) {
    console.error('Failed to load saved mock state', e)
  }

  return {
    users: INITIAL_USERS,
    exams: INITIAL_EXAMS,
    questions: INITIAL_QUESTIONS,
    students: INITIAL_STUDENTS,
    sheets: INITIAL_SHEETS,
    documents: INITIAL_DOCUMENTS,
    answers: INITIAL_ANSWERS,
    anomalies: INITIAL_ANOMALIES,
    processingStatus: { 1: INITIAL_PROCESSING_STATUS },
    results: { 1: INITIAL_RESULTS },
    currentUser: INITIAL_USERS[0], // default admin
  }
}

let state: MockState = loadInitialState()

function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch (e) {
    console.error('Failed to persist mock state', e)
  }
}

export const mockService = {
  resetState() {
    localStorage.removeItem(STORAGE_KEY)
    state = loadInitialState()
    persist()
  },

  // Auth
  async login(email: string): Promise<{ access_token: string; token_type: string; expires_in: number; user: User }> {
    const user = state.users.find(u => u.email.toLowerCase() === email.toLowerCase())
    if (!user) {
      throw { error: { code: 'INVALID_CREDENTIALS', message: 'Invalid email or password' } }
    }
    if (!user.is_active) {
      throw { error: { code: 'USER_INACTIVE', message: 'Account is deactivated' } }
    }
    state.currentUser = user
    persist()
    return {
      access_token: `mock-jwt-token-${user.role}-${user.id}`,
      token_type: 'bearer',
      expires_in: 28800,
      user,
    }
  },

  async getMe(): Promise<User> {
    if (!state.currentUser) {
      throw { error: { code: 'UNAUTHENTICATED', message: 'Not logged in' } }
    }
    return state.currentUser
  },

  setCurrentUserRole(role: 'admin' | 'examiner' | 'moderator') {
    const user = state.users.find(u => u.role === role)
    if (user) {
      state.currentUser = user
      persist()
    }
  },

  // Users
  async getUsers(): Promise<{ items: User[]; total: number; page: number; page_size: number }> {
    return { items: state.users, total: state.users.length, page: 1, page_size: 50 }
  },

  async createUser(data: { email: string; full_name: string; role: 'admin' | 'examiner' | 'moderator'; password?: string }): Promise<User> {
    if (state.users.some(u => u.email.toLowerCase() === data.email.toLowerCase())) {
      throw { error: { code: 'EMAIL_EXISTS', message: 'User with this email already exists' } }
    }
    const newUser: User = {
      id: Date.now(),
      email: data.email,
      full_name: data.full_name,
      role: data.role,
      is_active: true,
      created_at: new Date().toISOString(),
    }
    state.users.push(newUser)
    persist()
    return newUser
  },

  async updateUser(id: number, data: Partial<User>): Promise<User> {
    const user = state.users.find(u => u.id === id)
    if (!user) throw { error: { code: 'NOT_FOUND', message: 'User not found' } }
    if (state.currentUser?.id === id && data.is_active === false) {
      throw { error: { code: 'CANNOT_DEACTIVATE_SELF', message: 'You cannot deactivate your own account' } }
    }
    Object.assign(user, data)
    persist()
    return user
  },

  // Exams
  async getExams(): Promise<Exam[]> {
    return state.exams
  },

  async getExam(id: number): Promise<ExamDetail> {
    const exam = state.exams.find(e => e.id === id)
    if (!exam) throw { error: { code: 'NOT_FOUND', message: 'Exam not found' } }
    const questions = state.questions.filter(q => q.exam_id === id)
    const sheets = state.sheets.filter(s => s.exam_id === id)
    const answers = state.answers.filter(a => a.exam_id === id)
    return {
      ...exam,
      question_count: questions.length,
      sheet_count: sheets.length,
      answer_count: answers.length,
    }
  },

  async createExam(data: { title: string; course_code: string; exam_date?: string | null; settings?: any }): Promise<Exam> {
    const newExam: Exam = {
      id: Date.now(),
      title: data.title,
      course_code: data.course_code,
      exam_date: data.exam_date || null,
      status: 'draft',
      settings: data.settings || {
        ocr_low_conf_threshold: 0.80,
        ai_low_conf_threshold: 0.70,
        ai_disagreement_ratio: 0.30,
        too_fast_seconds: 10,
        z_threshold: 2.5,
        min_sample_size: 10,
        retrieval_top_k: 4,
        retrieval_min_score: 0.50,
      },
      created_at: new Date().toISOString(),
    }
    state.exams.unshift(newExam)
    persist()
    return newExam
  },

  async updateExam(id: number, data: Partial<Exam>): Promise<Exam> {
    const exam = state.exams.find(e => e.id === id)
    if (!exam) throw { error: { code: 'NOT_FOUND', message: 'Exam not found' } }
    Object.assign(exam, data)
    persist()
    return exam
  },

  async transitionExam(id: number, to: 'evaluation' | 'moderation' | 'completed'): Promise<Exam> {
    const exam = state.exams.find(e => e.id === id)
    if (!exam) throw { error: { code: 'NOT_FOUND', message: 'Exam not found' } }

    const failures: string[] = []

    if (to === 'evaluation') {
      const questions = state.questions.filter(q => q.exam_id === id)
      if (questions.length === 0) {
        failures.push('Exam must have at least one question.')
      }
      for (const q of questions) {
        if (!q.rubric || q.rubric.criteria.length === 0) {
          failures.push(`Question ${q.question_number} is missing a rubric.`)
        } else {
          const sum = q.rubric.criteria.reduce((s, c) => s + c.max_marks, 0)
          if (sum !== q.max_marks) {
            failures.push(`Question ${q.question_number} rubric criteria sum (${sum}) does not match max marks (${q.max_marks}).`)
          }
        }
        if (q.evaluation_mode === 'reference_grounded') {
          const docs = state.documents.filter(d => d.exam_id === id && d.status === 'indexed')
          if (docs.length === 0) {
            failures.push(`Question ${q.question_number} is reference-grounded but no indexed reference documents exist for this exam.`)
          }
        }
      }
      const sheets = state.sheets.filter(s => s.exam_id === id)
      if (sheets.length === 0) {
        failures.push('At least one answer sheet must be uploaded and mapped.')
      }
    } else if (to === 'moderation') {
      // Auto-run anomalies on moderation transition
      this.detectAnomalies(id)
    } else if (to === 'completed') {
      const pendingAnswers = state.answers.filter(a => a.exam_id === id && a.marking_status === 'pending')
      if (pendingAnswers.length > 0) {
        failures.push(`${pendingAnswers.length} attempted answer(s) are still pending evaluation.`)
      }
      const highAnomalies = state.anomalies.filter(a => a.exam_id === id && a.status === 'open' && a.severity === 'high')
      if (highAnomalies.length > 0) {
        failures.push(`${highAnomalies.length} high-severity open anomaly(ies) must be resolved or dismissed before completing the exam.`)
      }
    }

    if (failures.length > 0) {
      throw {
        error: {
          code: 'PRECONDITION_FAILED',
          message: 'Exam lifecycle transition failed. Please address the requirements below.',
          details: { failures },
        },
      }
    }

    exam.status = to
    persist()
    return exam
  },

  // Questions & Rubrics
  async getQuestions(examId: number): Promise<Question[]> {
    return state.questions.filter(q => q.exam_id === examId)
  },

  async createQuestion(examId: number, data: { question_number: string; text: string; max_marks: number; evaluation_mode?: 'standard' | 'reference_grounded' }): Promise<Question> {
    const exam = state.exams.find(e => e.id === examId)
    if (exam && exam.status !== 'draft') {
      throw { error: { code: 'EXAM_LOCKED', message: 'Questions can only be added to exams in draft status' } }
    }
    const newQuestion: Question = {
      id: Date.now(),
      exam_id: examId,
      question_number: data.question_number,
      text: data.text,
      max_marks: data.max_marks,
      evaluation_mode: data.evaluation_mode || 'standard',
      display_order: state.questions.filter(q => q.exam_id === examId).length + 1,
      rubric: {
        question_id: Date.now(),
        criteria: [],
        guidance: '',
      },
    }
    state.questions.push(newQuestion)
    persist()
    return newQuestion
  },

  async updateQuestion(id: number, data: Partial<Question>): Promise<Question> {
    const question = state.questions.find(q => q.id === id)
    if (!question) throw { error: { code: 'NOT_FOUND', message: 'Question not found' } }
    Object.assign(question, data)
    persist()
    return question
  },

  async deleteQuestion(id: number): Promise<void> {
    const question = state.questions.find(q => q.id === id)
    if (!question) throw { error: { code: 'NOT_FOUND', message: 'Question not found' } }
    const exam = state.exams.find(e => e.id === question.exam_id)
    if (exam && exam.status !== 'draft') {
      throw { error: { code: 'EXAM_LOCKED', message: 'Questions can only be deleted from draft exams' } }
    }
    state.questions = state.questions.filter(q => q.id !== id)
    persist()
  },

  async saveRubric(questionId: number, data: { criteria: { id: string; name: string; max_marks: number; description?: string }[]; guidance?: string }): Promise<Rubric> {
    const question = state.questions.find(q => q.id === questionId)
    if (!question) throw { error: { code: 'NOT_FOUND', message: 'Question not found' } }
    const sum = data.criteria.reduce((s, c) => s + Number(c.max_marks), 0)
    if (Math.abs(sum - question.max_marks) > 0.001) {
      throw {
        error: {
          code: 'RUBRIC_SUM_MISMATCH',
          message: `Criteria sum (${sum}) must equal question max marks (${question.max_marks})`,
        },
      }
    }
    const rubric: Rubric = {
      question_id: questionId,
      criteria: data.criteria,
      guidance: data.guidance,
    }
    question.rubric = rubric
    persist()
    return rubric
  },

  // Students & Answer Sheets
  async getStudents(): Promise<{ items: Student[]; total: number; page: number; page_size: number }> {
    return { items: state.students, total: state.students.length, page: 1, page_size: 100 }
  },

  async createStudent(data: { roll_number: string; full_name: string; department?: string }): Promise<Student> {
    const student: Student = {
      id: Date.now(),
      roll_number: data.roll_number,
      full_name: data.full_name,
      department: data.department || null,
      created_at: new Date().toISOString(),
    }
    state.students.push(student)
    persist()
    return student
  },

  async getSheets(examId: number): Promise<{ items: AnswerSheet[]; total: number; page: number; page_size: number }> {
    const items = state.sheets.filter(s => s.exam_id === examId)
    return { items, total: items.length, page: 1, page_size: 50 }
  },

  async uploadSheet(examId: number, studentId: number, pageCount: number = 3): Promise<AnswerSheet> {
    const student = state.students.find(s => s.id === studentId)
    const anonCode = `S-${Math.floor(1000 + Math.random() * 9000)}`
    const sheet: AnswerSheet = {
      id: Date.now(),
      exam_id: examId,
      student_id: studentId,
      anon_code: anonCode,
      status: 'uploaded',
      page_count: pageCount,
      created_at: new Date().toISOString(),
      student,
      mapped: false,
      answers_total: 0,
      answers_marked: 0,
    }
    state.sheets.push(sheet)
    persist()
    return sheet
  },

  async getSheetDetail(sheetId: number): Promise<AnswerSheetDetail> {
    const sheet = state.sheets.find(s => s.id === sheetId)
    if (!sheet) throw { error: { code: 'NOT_FOUND', message: 'Sheet not found' } }
    const pages = Array.from({ length: sheet.page_count }, (_, i) => ({
      id: sheetId * 10 + i + 1,
      sheet_id: sheetId,
      page_number: i + 1,
      image_url: SAMPLE_PAGE_SVG,
    }))
    const answers = state.answers
      .filter(a => a.anon_code === sheet.anon_code)
      .map(a => ({
        id: a.id,
        question_id: a.question.id,
        question_number: a.question.question_number,
        is_attempted: a.is_attempted,
        page_start: 1,
        page_end: 1,
        marking_status: a.marking_status,
        final_marks: a.final_marks,
      }))

    return {
      ...sheet,
      pages,
      answers,
    }
  },

  async savePageMapping(sheetId: number, items: { question_id: number; page_start: number; page_end: number; is_attempted: boolean }[]): Promise<any[]> {
    const sheet = state.sheets.find(s => s.id === sheetId)
    if (!sheet) throw { error: { code: 'NOT_FOUND', message: 'Sheet not found' } }
    sheet.status = 'mapped'
    sheet.mapped = true
    sheet.answers_total = items.length
    persist()
    return items
  },

  async assignExaminers(_examId: number, examinerIds: number[], _strategy: string): Promise<{ assigned: number; per_examiner: Record<string, number> }> {
    const perExaminer: Record<string, number> = {}
    examinerIds.forEach(id => {
      perExaminer[id] = 4
    })
    return {
      assigned: examinerIds.length * 4,
      per_examiner: perExaminer,
    }
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
  }): Promise<{ items: AnswerRow[]; total: number; page: number; page_size: number }> {
    let list = state.answers.filter(a => a.exam_id === Number(params.exam_id))
    if (params.sheet_id) {
      const sheet = state.sheets.find(s => s.id === Number(params.sheet_id))
      if (sheet) {
        list = list.filter(a => a.anon_code === sheet.anon_code)
      }
    }
    if (params.question_id) {
      list = list.filter(a => a.question.id === Number(params.question_id))
    }
    if (params.marking_status && params.marking_status !== 'all') {
      list = list.filter(a => a.marking_status === params.marking_status)
    }
    if (params.ocr_review_required) {
      list = list.filter(a => a.ocr.review_required && !a.ocr.verified)
    }
    const page = Number(params.page) || 1
    const pageSize = Number(params.page_size) || 25
    const total = list.length
    const start = (page - 1) * pageSize
    const paginated = list.slice(start, start + pageSize)
    const rows: AnswerRow[] = paginated.map(a => ({
      id: a.id,
      anon_code: a.anon_code,
      question_number: a.question.question_number,
      marking_status: a.marking_status,
      ocr_status: a.ocr.status,
      ai_status: a.ai.status,
      ocr_review_required: a.ocr.review_required,
      final_marks: a.final_marks,
      max_marks: a.question.max_marks,
    }))
    return { items: rows, total, page, page_size: pageSize }
  },

  async getAnswerDetail(id: number): Promise<AnswerDetail> {
    const answer = state.answers.find(a => a.id === Number(id))
    if (!answer) throw { error: { code: 'NOT_FOUND', message: 'Answer not found' } }
    return answer
  },

  async rerunSingleOcr(id: number): Promise<{ queued: number }> {
    const answer = state.answers.find(a => a.id === Number(id))
    if (!answer) throw { error: { code: 'NOT_FOUND', message: 'Answer not found' } }
    answer.ocr.status = 'done'
    answer.ocr.verified = false
    persist()
    return { queued: 1 }
  },

  async updateAnswerText(id: number, data: { verified_text?: string; ocr_verified?: boolean }): Promise<any> {
    const answer = state.answers.find(a => a.id === Number(id))
    if (!answer) throw { error: { code: 'NOT_FOUND', message: 'Answer not found' } }

    if (data.verified_text !== undefined) {
      answer.ocr.verified_text = data.verified_text
      answer.ocr.text = data.verified_text
    }
    if (data.ocr_verified !== undefined) {
      answer.ocr.verified = data.ocr_verified
      answer.ocr.review_required = !data.ocr_verified
    }
    // When text changes, mark AI suggestion stale!
    if (answer.ai.latest) {
      answer.ai.latest.stale = true
    }
    persist()
    return answer.ocr
  },

  async runAiEvaluation(id: number, forceStandard?: boolean): Promise<AiEvaluation> {
    const answer = state.answers.find(a => a.id === Number(id))
    if (!answer) throw { error: { code: 'NOT_FOUND', message: 'Answer not found' } }

    const mode = forceStandard ? 'standard' : answer.question.evaluation_mode
    const maxMarks = answer.question.max_marks
    const rubricCriteria = answer.rubric.criteria

    // Formulate realistic criteria scores
    const criteriaScores = rubricCriteria.map(c => {
      const awarded = Math.round((c.max_marks * 0.85) * 2) / 2
      return {
        criterion_id: c.id,
        criterion: c.name,
        max_marks: c.max_marks,
        awarded_marks: awarded,
        reason: `Demonstrates solid grasp of ${c.name}. Minor points omitted.`,
      }
    })

    const totalAwarded = criteriaScores.reduce((sum, c) => sum + c.awarded_marks, 0)

    const newAi: AiEvaluation = {
      id: Date.now(),
      answer_id: answer.id,
      mode_requested: answer.question.evaluation_mode,
      mode_used: mode,
      model_name: 'gemini-1.5-pro',
      prompt_version: 'v1.0',
      suggested_marks: totalAwarded,
      max_marks: maxMarks,
      confidence: 0.88,
      llm_confidence: 0.90,
      criteria: criteriaScores,
      overall_reason: `Evaluated against rubric. ${mode === 'reference_grounded' ? 'Grounded in reference documents.' : 'Standard rubric evaluation.'}`,
      warnings: [],
      stale: false,
      created_at: new Date().toISOString(),
    }

    answer.ai.status = 'done'
    answer.ai.latest = newAi
    persist()
    return newAi
  },

  async acceptAi(id: number, _aiEvaluationId: number, _activeSeconds: number): Promise<any> {
    const answer = state.answers.find(a => a.id === Number(id))
    if (!answer) throw { error: { code: 'NOT_FOUND', message: 'Answer not found' } }

    if (answer.ocr.review_required && !answer.ocr.verified) {
      throw { error: { code: 'OCR_NOT_VERIFIED', message: 'Low-confidence OCR text must be verified before accepting AI marks' } }
    }
    if (!answer.ai.latest || answer.ai.latest.stale) {
      throw { error: { code: 'AI_EVAL_STALE', message: 'AI suggestion is stale or missing. Please re-run AI evaluation' } }
    }

    const marks = answer.ai.latest.suggested_marks
    const criterionMarks: Record<string, number> = {}
    answer.ai.latest.criteria.forEach(c => {
      criterionMarks[c.criterion_id] = c.awarded_marks
    })

    answer.evaluation = {
      id: Date.now(),
      marks_awarded: marks,
      criterion_marks: criterionMarks,
      comment: 'Accepted AI recommendation',
      source: 'ai_accepted',
      status: 'submitted',
      submitted_at: new Date().toISOString(),
      examiner: { id: state.currentUser?.id || 2, full_name: state.currentUser?.full_name || 'Dr. Alan Turing' },
    }
    answer.final_marks = marks
    answer.final_source = 'examiner'
    answer.marking_status = 'marked'

    persist()
    return answer.evaluation
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
    const answer = state.answers.find(a => a.id === Number(id))
    if (!answer) throw { error: { code: 'NOT_FOUND', message: 'Answer not found' } }

    if (data.marks_awarded < 0 || data.marks_awarded > answer.question.max_marks) {
      throw { error: { code: 'MARKS_OUT_OF_RANGE', message: `Marks must be between 0 and ${answer.question.max_marks}` } }
    }

    if (data.criterion_marks) {
      const sum = Object.values(data.criterion_marks).reduce((a, b) => a + Number(b), 0)
      if (Math.abs(sum - data.marks_awarded) > 0.001) {
        throw { error: { code: 'CRITERIA_SUM_MISMATCH', message: `Sum of criteria (${sum}) does not match total marks (${data.marks_awarded})` } }
      }
    }

    answer.evaluation = {
      id: Date.now(),
      marks_awarded: data.marks_awarded,
      criterion_marks: data.criterion_marks,
      comment: data.comment,
      source: data.source,
      status: data.submit ? 'submitted' : 'draft',
      submitted_at: new Date().toISOString(),
      examiner: { id: state.currentUser?.id || 2, full_name: state.currentUser?.full_name || 'Dr. Alan Turing' },
    }

    if (data.submit) {
      answer.final_marks = data.marks_awarded
      answer.final_source = 'examiner'
      answer.marking_status = 'marked'
    }

    persist()
    return answer.evaluation
  },

  // Reference Documents
  async getDocuments(examId: number): Promise<ReferenceDoc[]> {
    return state.documents.filter(d => d.exam_id === examId)
  },

  async uploadDocument(examId: number, title: string, docType: any, questionId?: number): Promise<ReferenceDoc> {
    const newDoc: ReferenceDoc = {
      id: Date.now(),
      exam_id: examId,
      question_id: questionId || null,
      title,
      doc_type: docType,
      status: 'indexed',
      chunk_count: 10,
      error: null,
      created_at: new Date().toISOString(),
    }
    state.documents.push(newDoc)
    persist()
    return newDoc
  },

  async deleteDocument(id: number): Promise<void> {
    state.documents = state.documents.filter(d => d.id !== id)
    persist()
  },

  async searchReference(_examId: number, _query: string): Promise<{ chunks: any[] }> {
    return {
      chunks: [
        {
          doc_id: 1,
          title: 'Raft Consensus Protocol & Fault Tolerance Guide.pdf',
          chunk_index: 2,
          score: 0.89,
          text: 'Section 5.2 Leader Election: When followers do not receive heartbeats within electionTimeout, they increment their term and transition to candidate state.',
        },
        {
          doc_id: 1,
          title: 'Raft Consensus Protocol & Fault Tolerance Guide.pdf',
          chunk_index: 5,
          score: 0.81,
          text: 'Section 5.3 Log Replication: Leaders accept client commands, append to log, and issue AppendEntries RPC to followers.',
        },
      ],
    }
  },

  // Moderation
  async getModerationQueue(examId: number): Promise<{ items: ModerationQueueItem[]; total: number; page: number; page_size: number }> {
    const flagged = state.answers.filter(a => a.exam_id === examId && (a.marking_status === 'flagged' || (a.anomalies && a.anomalies.length > 0)))
    const items: ModerationQueueItem[] = flagged.map(a => ({
      answer_id: a.id,
      anon_code: a.anon_code,
      question_number: a.question.question_number,
      examiner: a.evaluation?.examiner || { id: 2, full_name: 'Dr. Alan Turing' },
      marks: a.final_marks ?? 0,
      ai_suggested_marks: a.ai.latest?.suggested_marks ?? null,
      anomalies: (a.anomalies || []).map(an => ({ type: an.type, severity: an.severity })),
    }))
    return { items, total: items.length, page: 1, page_size: 50 }
  },

  async submitModeration(id: number, data: { decision: 'confirmed' | 'overridden'; moderated_marks: number; reason?: string }): Promise<any> {
    const answer = state.answers.find(a => a.id === Number(id))
    if (!answer) throw { error: { code: 'NOT_FOUND', message: 'Answer not found' } }

    if (data.decision === 'overridden' && (!data.reason || data.reason.trim().length === 0)) {
      throw { error: { code: 'REASON_REQUIRED', message: 'A written justification reason is required when overriding marks' } }
    }

    answer.moderation = {
      id: Date.now(),
      answer_id: answer.id,
      decision: data.decision,
      moderated_marks: data.moderated_marks,
      reason: data.reason,
      moderator: { id: state.currentUser?.id || 3, full_name: state.currentUser?.full_name || 'Dean Grace Hopper' },
      created_at: new Date().toISOString(),
    }

    answer.final_marks = data.moderated_marks
    answer.final_source = 'moderator'
    answer.marking_status = 'moderated'

    // Resolve anomalies attached to this answer
    state.anomalies.forEach(an => {
      if (an.answer_id === answer.id) {
        an.status = 'resolved'
      }
    })

    persist()
    return answer.moderation
  },

  // Anomalies
  async detectAnomalies(examId: number): Promise<{ created: number; updated: number; by_type: Record<string, number> }> {
    return {
      created: state.anomalies.filter(a => a.exam_id === examId).length,
      updated: 0,
      by_type: {
        AI_DISAGREEMENT: 1,
        UNCHECKED_ANSWER: 1,
        EXAMINER_DEVIATION: 1,
      },
    }
  },

  async getAnomalies(examId: number): Promise<{ items: Anomaly[]; total: number; page: number; page_size: number }> {
    const list = state.anomalies.filter(a => a.exam_id === examId)
    return { items: list, total: list.length, page: 1, page_size: 50 }
  },

  async updateAnomaly(id: number, status: 'dismissed' | 'open', note?: string): Promise<Anomaly> {
    const anomaly = state.anomalies.find(a => a.id === id)
    if (!anomaly) throw { error: { code: 'NOT_FOUND', message: 'Anomaly not found' } }
    if (anomaly.status === 'resolved') {
      throw { error: { code: 'ALREADY_RESOLVED', message: 'Resolved anomalies cannot be reopened or dismissed' } }
    }
    anomaly.status = status
    if (note) anomaly.note = note
    persist()
    return anomaly
  },

  // Processing status & batch runs
  async getProcessingStatus(examId: number): Promise<ProcessingStatus> {
    return state.processingStatus[examId] || INITIAL_PROCESSING_STATUS
  },

  async runBatchOcr(examId: number): Promise<{ queued: number }> {
    const status = state.processingStatus[examId] || { ...INITIAL_PROCESSING_STATUS }
    status.ocr.done += 1
    state.processingStatus[examId] = status
    persist()
    return { queued: 12 }
  },

  async runBatchAi(examId: number): Promise<{ queued: number }> {
    const status = state.processingStatus[examId] || { ...INITIAL_PROCESSING_STATUS }
    status.ai.done += 1
    state.processingStatus[examId] = status
    persist()
    return { queued: 12 }
  },

  // Analytics
  async getAnalyticsOverview(_examId: number): Promise<AnalyticsOverview> {
    return INITIAL_ANALYTICS_OVERVIEW
  },

  async getExaminerAnalytics(_examId: number): Promise<ExaminerAnalytics[]> {
    return INITIAL_EXAMINER_ANALYTICS
  },

  async getQuestionAnalytics(_examId: number): Promise<QuestionAnalytics[]> {
    return INITIAL_QUESTION_ANALYTICS
  },

  async getMyProgress(_examId: number): Promise<ExaminerProgress> {
    return {
      assigned: 6,
      marked: 4,
      remaining: 2,
      review_required: 1,
      avg_seconds: 42.5,
    }
  },

  // Results
  async computeResults(_examId: number): Promise<{ computed: boolean }> {
    return { computed: true }
  },

  async getResults(examId: number): Promise<ExamResults> {
    return state.results[examId] || INITIAL_RESULTS
  },

  async getResultDetail(id: number): Promise<ResultDetail> {
    const resultItem = (state.results[1]?.items || INITIAL_RESULTS.items).find(r => r.id === id) || INITIAL_RESULTS.items[0]
    return {
      result: resultItem,
      breakdown: [
        { question_number: '1', marks: 5.0, max_marks: 5.0, final_source: 'examiner' },
        { question_number: '2', marks: 8.5, max_marks: 10.0, final_source: 'moderator' },
        { question_number: '3', marks: 11.5, max_marks: 15.0, final_source: 'examiner' },
      ],
    }
  },

  async publishResults(examId: number): Promise<{ published: boolean }> {
    const exam = state.exams.find(e => e.id === examId)
    if (exam) {
      exam.status = 'completed'
    }
    const res = state.results[examId] || INITIAL_RESULTS
    res.items.forEach(i => (i.status = 'published'))
    persist()
    return { published: true }
  },
}
