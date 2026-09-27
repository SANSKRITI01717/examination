import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { useToast } from '../../components/ui/Toast'
import { EXAM_STATUS_COLORS, type ExamStatus } from '../../lib/constants'

export const ExamDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const isNew = !id || id === 'new'
  const examId = isNew ? null : Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast, errorToast } = useToast()

  const [title, setTitle] = useState('')
  const [courseCode, setCourseCode] = useState('')
  const [examDate, setExamDate] = useState('')
  const [ocrThreshold, setOcrThreshold] = useState('0.80')
  const [aiThreshold, setAiThreshold] = useState('0.70')
  const [failures, setFailures] = useState<string[]>([])

  const { data: exam } = useQuery({
    queryKey: ['exam', examId],
    queryFn: () => (examId ? apiClient.getExam(examId) : null),
    enabled: Boolean(examId),
  })

  useEffect(() => {
    if (exam) {
      setTitle(exam.title)
      setCourseCode(exam.course_code)
      setExamDate(exam.exam_date || '')
      setOcrThreshold(String(exam.settings?.ocr_low_conf_threshold ?? 0.8))
      setAiThreshold(String(exam.settings?.ai_low_conf_threshold ?? 0.7))
    }
  }, [exam])

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        title,
        course_code: courseCode,
        exam_date: examDate || null,
        settings: {
          ocr_low_conf_threshold: parseFloat(ocrThreshold) || 0.8,
          ai_low_conf_threshold: parseFloat(aiThreshold) || 0.7,
        },
      }
      if (isNew) {
        return apiClient.createExam(payload)
      } else {
        return apiClient.updateExam(examId!, payload)
      }
    },
    onSuccess: (savedExam: any) => {
      queryClient.invalidateQueries({ queryKey: ['exams'] })
      queryClient.invalidateQueries({ queryKey: ['exam', savedExam.id] })
      toast(isNew ? 'Exam created successfully' : 'Exam settings updated', 'success')
      if (isNew) {
        navigate(`/admin/exams/${savedExam.id}`)
      }
    },
    onError: err => errorToast(err),
  })

  const transitionMutation = useMutation({
    mutationFn: (to: 'evaluation' | 'moderation' | 'completed') =>
      apiClient.transitionExam(examId!, to),
    onSuccess: (updatedExam: any) => {
      setFailures([])
      queryClient.invalidateQueries({ queryKey: ['exams'] })
      queryClient.invalidateQueries({ queryKey: ['exam', examId] })
      toast(`Exam transitioned to ${updatedExam.status}`, 'success')
    },
    onError: (err: any) => {
      if (err?.error?.details?.failures) {
        setFailures(err.error.details.failures)
      } else {
        errorToast(err)
      }
    },
  })

  const currentStatus: ExamStatus = exam?.status || 'draft'
  const statusColor = EXAM_STATUS_COLORS[currentStatus] || EXAM_STATUS_COLORS.draft

  const steps: { key: ExamStatus; label: string }[] = [
    { key: 'draft', label: 'Draft' },
    { key: 'evaluation', label: 'Evaluation' },
    { key: 'moderation', label: 'Moderation' },
    { key: 'completed', label: 'Completed' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-bold text-slate-900">
              {isNew ? 'New Examination' : exam?.title}
            </h2>
            {!isNew && (
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${statusColor.bg} ${statusColor.text} ${statusColor.border}`}
              >
                {currentStatus}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            {isNew ? 'Set up a new examination cycle' : `Course: ${exam?.course_code} • ID: #${exam?.id}`}
          </p>
        </div>

        {!isNew && (
          <div className="flex flex-wrap items-center gap-2">
            <Link to={`/admin/exams/${examId}/questions`}>
              <Button size="sm" variant="outline">
                Questions & Rubrics ({exam?.question_count ?? 0})
              </Button>
            </Link>
            <Link to={`/admin/exams/${examId}/references`}>
              <Button size="sm" variant="outline">
                Reference Docs
              </Button>
            </Link>
            <Link to={`/admin/exams/${examId}/sheets`}>
              <Button size="sm" variant="outline">
                Answer Sheets ({exam?.sheet_count ?? 0})
              </Button>
            </Link>
            <Link to={`/admin/exams/${examId}/processing`}>
              <Button size="sm" variant="secondary">
                Processing
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* Lifecycle Stepper (E5) */}
      {!isNew && (
        <Card title="Lifecycle Progression">
          <div className="flex items-center justify-between py-2 overflow-x-auto">
            {steps.map((step, idx) => {
              const isPastOrCurrent =
                steps.findIndex(s => s.key === currentStatus) >= idx
              const isCurrent = step.key === currentStatus

              return (
                <React.Fragment key={step.key}>
                  <div className="flex flex-col items-center flex-shrink-0">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                        isCurrent
                          ? 'bg-indigo-600 text-white ring-4 ring-indigo-100'
                          : isPastOrCurrent
                          ? 'bg-emerald-600 text-white'
                          : 'bg-slate-200 text-slate-500'
                      }`}
                    >
                      {idx + 1}
                    </div>
                    <span
                      className={`text-xs mt-1.5 font-medium capitalize ${
                        isCurrent ? 'text-indigo-600 font-bold' : 'text-slate-600'
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                  {idx < steps.length - 1 && (
                    <div
                      className={`flex-1 h-0.5 mx-2 min-w-8 ${
                        steps.findIndex(s => s.key === currentStatus) > idx
                          ? 'bg-emerald-500'
                          : 'bg-slate-200'
                      }`}
                    />
                  )}
                </React.Fragment>
              )
            })}
          </div>

          {/* Lifecycle Transition Buttons */}
          <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between flex-wrap gap-2">
            <span className="text-xs text-slate-500">
              Exam is currently in <strong className="capitalize">{currentStatus}</strong> mode.
            </span>
            <div className="flex items-center space-x-2">
              {currentStatus === 'draft' && (
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => transitionMutation.mutate('evaluation')}
                  isLoading={transitionMutation.isPending}
                >
                  Move to Evaluation ➔
                </Button>
              )}
              {currentStatus === 'evaluation' && (
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => transitionMutation.mutate('moderation')}
                  isLoading={transitionMutation.isPending}
                >
                  Move to Moderation ➔
                </Button>
              )}
              {currentStatus === 'moderation' && (
                <Button
                  size="sm"
                  variant="success"
                  onClick={() => transitionMutation.mutate('completed')}
                  isLoading={transitionMutation.isPending}
                >
                  Complete Exam ➔
                </Button>
              )}
            </div>
          </div>

          {/* Precondition Failure Notice */}
          {failures.length > 0 && (
            <div className="mt-4 p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800">
              <h5 className="font-bold mb-1">Cannot Transition Lifecycle:</h5>
              <ul className="list-disc pl-4 space-y-0.5">
                {failures.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {/* Main Settings Form */}
      <Card title="Exam Configuration & Thresholds">
        <form
          onSubmit={e => {
            e.preventDefault()
            saveMutation.mutate()
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Course Code"
              required
              value={courseCode}
              onChange={e => setCourseCode(e.target.value)}
              placeholder="e.g. CS-402"
            />
            <Input
              label="Exam Date"
              type="date"
              value={examDate}
              onChange={e => setExamDate(e.target.value)}
            />
          </div>

          <Input
            label="Exam Title"
            required
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="e.g. Computer Networks & Distributed Systems"
          />

          <div className="pt-3 border-t border-slate-100">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Quality & AI Thresholds
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Low OCR Confidence Threshold (0.0 – 1.0)"
                type="number"
                step="0.05"
                min="0"
                max="1"
                value={ocrThreshold}
                onChange={e => setOcrThreshold(e.target.value)}
                helperText="Answers below this require examiner confirmation before AI acceptance (Default 0.80)"
              />
              <Input
                label="AI Low Confidence Threshold (0.0 – 1.0)"
                type="number"
                step="0.05"
                min="0"
                max="1"
                value={aiThreshold}
                onChange={e => setAiThreshold(e.target.value)}
                helperText="Flags low AI confidence warning in examiner workspace (Default 0.70)"
              />
            </div>
          </div>

          <div className="flex justify-end pt-3 border-t border-slate-100">
            <Button variant="primary" type="submit" isLoading={saveMutation.isPending}>
              {isNew ? 'Create Examination' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
