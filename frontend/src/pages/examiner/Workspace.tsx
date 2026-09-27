import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { QuestionNav } from '../../components/workspace/QuestionNav'
import { PageViewer } from '../../components/workspace/PageViewer'
import { RubricPanel } from '../../components/workspace/RubricPanel'
import { OcrPanel } from '../../components/workspace/OcrPanel'
import { AiSuggestionPanel } from '../../components/workspace/AiSuggestionPanel'
import { MarkingPanel } from '../../components/workspace/MarkingPanel'
import { useToast } from '../../components/ui/Toast'

export const Workspace: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const answerId = Number(id || 812)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast, errorToast } = useToast()

  // Mobile view tab state: 'image' | 'text' | 'ai' | 'marks'
  const [mobileTab, setMobileTab] = useState<'image' | 'text' | 'ai' | 'marks'>('image')
  const [serverError, setServerError] = useState<string | null>(null)

  // Fetch full answer workspace detail (N2)
  const { data: answer, isLoading } = useQuery({
    queryKey: ['answerDetail', answerId],
    queryFn: () => apiClient.getAnswerDetail(answerId),
  })

  // Fetch all answers for script navigation
  const { data: answersData } = useQuery({
    queryKey: ['answers', answer?.exam_id],
    queryFn: () => (answer ? apiClient.getAnswers({ exam_id: answer.exam_id }) : null),
    enabled: Boolean(answer?.exam_id),
  })

  // Save OCR text (O3)
  const saveTextMutation = useMutation({
    mutationFn: (data: { verified_text: string; ocr_verified: boolean }) =>
      apiClient.updateAnswerText(answerId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['answerDetail', answerId] })
      toast('OCR text updated and verified', 'success')
    },
    onError: err => errorToast(err),
  })

  // Re-run single answer OCR (O2)
  const rerunOcrMutation = useMutation({
    mutationFn: () => apiClient.rerunSingleOcr(answerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['answerDetail', answerId] })
      toast('OCR re-processing queued for this answer', 'success')
    },
    onError: err => errorToast(err),
  })

  // Run AI evaluation (V1)
  const runAiMutation = useMutation({
    mutationFn: () => apiClient.runAiEvaluation(answerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['answerDetail', answerId] })
      toast('AI evaluation refreshed', 'success')
    },
    onError: err => errorToast(err),
  })

  // Accept AI suggestion (M1)
  const acceptAiMutation = useMutation({
    mutationFn: ({ aiEvaluationId, activeSeconds }: { aiEvaluationId: number; activeSeconds: number }) =>
      apiClient.acceptAi(answerId, aiEvaluationId, activeSeconds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['answerDetail', answerId] })
      queryClient.invalidateQueries({ queryKey: ['answers'] })
      queryClient.invalidateQueries({ queryKey: ['examinerProgress'] })
      toast('AI suggested marks accepted and recorded', 'success')
      if (answer?.navigation.next_answer_id) {
        navigate(`/examiner/answers/${answer.navigation.next_answer_id}`)
      }
    },
    onError: (err: any) => {
      const msg = err?.error?.message || 'Failed to accept AI marks'
      setServerError(msg)
      errorToast(msg)
    },
  })

  // Submit human marks (M2)
  const submitMarksMutation = useMutation({
    mutationFn: (data: any) => apiClient.submitEvaluation(answerId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['answerDetail', answerId] })
      queryClient.invalidateQueries({ queryKey: ['answers'] })
      queryClient.invalidateQueries({ queryKey: ['examinerProgress'] })
      toast('Marks submitted successfully', 'success')
      if (answer?.navigation.next_answer_id) {
        navigate(`/examiner/answers/${answer.navigation.next_answer_id}`)
      }
    },
    onError: (err: any) => {
      const msg = err?.error?.message || 'Failed to submit marks'
      setServerError(msg)
      errorToast(msg)
    },
  })

  // Keyboard Shortcuts per frontend-plan.md §4:
  // A: accept, N: next, P: previous, V: verify text
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) return

      if (e.key.toLowerCase() === 'n' && answer?.navigation.next_answer_id) {
        navigate(`/examiner/answers/${answer.navigation.next_answer_id}`)
      } else if (e.key.toLowerCase() === 'p' && answer?.navigation.prev_answer_id) {
        navigate(`/examiner/answers/${answer.navigation.prev_answer_id}`)
      } else if (e.key.toLowerCase() === 'v' && answer?.ocr) {
        saveTextMutation.mutate({
          verified_text: answer.ocr.verified_text || answer.ocr.text,
          ocr_verified: true,
        })
      }
    },
    [answer, navigate, saveTextMutation]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  if (isLoading || !answer) {
    return (
      <div className="flex h-[75vh] items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-indigo-600 border-r-transparent"></div>
          <p className="mt-2 text-xs text-slate-500 font-medium">Loading answer workspace...</p>
        </div>
      </div>
    )
  }

  const allNavAnswers =
    answersData?.items.map(a => ({
      id: a.id,
      question_number: a.question_number,
      anon_code: a.anon_code,
      marking_status: a.marking_status,
    })) || []

  return (
    <div className="flex flex-col h-[calc(100vh-5rem)]">
      {/* Workspace Top Header Bar */}
      <div className="bg-white border-b border-slate-200 px-4 py-2.5 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center space-x-3">
          <span className="text-sm font-black text-slate-900">
            Question {answer.question.question_number}
          </span>
          <span className="text-xs font-mono font-bold text-indigo-600 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200">
            Candidate: {answer.anon_code}
          </span>
          <span className="text-xs text-slate-500 hidden sm:inline">
            Status: <strong className="capitalize">{answer.marking_status}</strong>
          </span>
        </div>

        <div className="flex items-center space-x-2 text-xs text-slate-500">
          <span className="hidden md:inline text-[11px] bg-slate-100 px-2 py-1 rounded text-slate-600 font-mono">
            Shortcuts: [V] Verify • [N] Next • [P] Prev
          </span>
        </div>
      </div>

      {/* Desktop 3-Column Layout (≥1024px) */}
      <div className="hidden lg:grid lg:grid-cols-12 gap-4 flex-1 p-4 overflow-hidden">
        {/* Column 1: Question Navigation (2 cols) */}
        <div className="lg:col-span-2 h-full overflow-hidden">
          <QuestionNav
            currentAnswerId={answer.id}
            examId={answer.exam_id}
            position={answer.navigation.position}
            total={answer.navigation.total}
            prevAnswerId={answer.navigation.prev_answer_id}
            nextAnswerId={answer.navigation.next_answer_id}
            allAnswers={allNavAnswers}
          />
        </div>

        {/* Column 2: Scanned Answer Page (5 cols) */}
        <div className="lg:col-span-5 h-full overflow-hidden">
          <PageViewer pages={answer.pages} />
        </div>

        {/* Column 3: Rubric + OCR + AI + Final Marking (5 cols) */}
        <div className="lg:col-span-5 h-full overflow-y-auto space-y-4 pr-1">
          <RubricPanel
            questionNumber={answer.question.question_number}
            questionText={answer.question.text}
            maxMarks={answer.question.max_marks}
            evaluationMode={answer.question.evaluation_mode}
            rubric={answer.rubric}
          />

          <OcrPanel
            ocr={answer.ocr}
            onSaveText={async (text, verify) => {
              await saveTextMutation.mutateAsync({ verified_text: text, ocr_verified: verify })
            }}
            onRerunOcr={async () => {
              await rerunOcrMutation.mutateAsync()
            }}
            isRerunningOcr={rerunOcrMutation.isPending}
          />

          <AiSuggestionPanel
            status={answer.ai.status}
            aiEvaluation={answer.ai.latest}
            onRunAi={async () => {
              await runAiMutation.mutateAsync()
            }}
            isRunningAi={runAiMutation.isPending}
          />

          <MarkingPanel
            maxMarks={answer.question.max_marks}
            rubric={answer.rubric}
            aiEvaluation={answer.ai.latest}
            existingEvaluation={answer.evaluation}
            isOcrVerified={answer.ocr.verified}
            ocrReviewRequired={answer.ocr.review_required}
            onAcceptAi={async (aiEvalId, activeSeconds) => {
              await acceptAiMutation.mutateAsync({ aiEvaluationId: aiEvalId, activeSeconds })
            }}
            onSubmitMarks={async data => {
              await submitMarksMutation.mutateAsync(data)
            }}
            isSubmitting={acceptAiMutation.isPending || submitMarksMutation.isPending}
            serverError={serverError}
          />
        </div>
      </div>

      {/* Mobile Responsive Layout (<1024px) */}
      <div className="lg:hidden flex flex-col flex-1 overflow-hidden">
        {/* Mobile Top Navigation Bar */}
        <div className="p-2 bg-slate-100 border-b border-slate-200 flex items-center justify-between text-xs">
          <button
            disabled={!answer.navigation.prev_answer_id}
            onClick={() => answer.navigation.prev_answer_id && navigate(`/examiner/answers/${answer.navigation.prev_answer_id}`)}
            className="px-3 py-1.5 rounded bg-white border border-slate-300 disabled:opacity-40"
          >
            ← Prev
          </button>
          <span className="font-semibold text-slate-700">
            {answer.navigation.position} / {answer.navigation.total}
          </span>
          <button
            disabled={!answer.navigation.next_answer_id}
            onClick={() => answer.navigation.next_answer_id && navigate(`/examiner/answers/${answer.navigation.next_answer_id}`)}
            className="px-3 py-1.5 rounded bg-white border border-slate-300 disabled:opacity-40"
          >
            Next →
          </button>
        </div>

        {/* Mobile Viewport Content */}
        <div className="flex-1 overflow-y-auto p-4 pb-20">
          {mobileTab === 'image' && <PageViewer pages={answer.pages} />}

          {mobileTab === 'text' && (
            <div className="space-y-4">
              <RubricPanel
                questionNumber={answer.question.question_number}
                questionText={answer.question.text}
                maxMarks={answer.question.max_marks}
                evaluationMode={answer.question.evaluation_mode}
                rubric={answer.rubric}
              />
              <OcrPanel
                ocr={answer.ocr}
                onSaveText={async (text, verify) => {
                  await saveTextMutation.mutateAsync({ verified_text: text, ocr_verified: verify })
                }}
                onRerunOcr={async () => {
                  await rerunOcrMutation.mutateAsync()
                }}
                isRerunningOcr={rerunOcrMutation.isPending}
              />
            </div>
          )}

          {mobileTab === 'ai' && (
            <AiSuggestionPanel
              status={answer.ai.status}
              aiEvaluation={answer.ai.latest}
              onRunAi={async () => {
                await runAiMutation.mutateAsync()
              }}
              isRunningAi={runAiMutation.isPending}
            />
          )}

          {mobileTab === 'marks' && (
            <MarkingPanel
              maxMarks={answer.question.max_marks}
              rubric={answer.rubric}
              aiEvaluation={answer.ai.latest}
              existingEvaluation={answer.evaluation}
              isOcrVerified={answer.ocr.verified}
              ocrReviewRequired={answer.ocr.review_required}
              onAcceptAi={async (aiEvalId, activeSeconds) => {
                await acceptAiMutation.mutateAsync({ aiEvaluationId: aiEvalId, activeSeconds })
              }}
              onSubmitMarks={async data => {
                await submitMarksMutation.mutateAsync(data)
              }}
              isSubmitting={acceptAiMutation.isPending || submitMarksMutation.isPending}
              serverError={serverError}
            />
          )}
        </div>

        {/* Mobile Sticky Bottom Tab Bar (Image | Text | AI | Marks) */}
        <div className="fixed bottom-0 left-0 right-0 z-30 bg-white border-t border-slate-200 grid grid-cols-4 p-1 shadow-lg">
          <button
            onClick={() => setMobileTab('image')}
            className={`py-2 text-xs font-bold text-center rounded-lg cursor-pointer ${
              mobileTab === 'image' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Image
          </button>
          <button
            onClick={() => setMobileTab('text')}
            className={`py-2 text-xs font-bold text-center rounded-lg cursor-pointer ${
              mobileTab === 'text' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Text
          </button>
          <button
            onClick={() => setMobileTab('ai')}
            className={`py-2 text-xs font-bold text-center rounded-lg cursor-pointer ${
              mobileTab === 'ai' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            AI Suggestion
          </button>
          <button
            onClick={() => setMobileTab('marks')}
            className={`py-2 text-xs font-bold text-center rounded-lg cursor-pointer ${
              mobileTab === 'marks' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Marking
          </button>
        </div>
      </div>
    </div>
  )
}
