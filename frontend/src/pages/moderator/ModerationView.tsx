import React, { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { PageViewer } from '../../components/workspace/PageViewer'
import { RubricPanel } from '../../components/workspace/RubricPanel'
import { OcrPanel } from '../../components/workspace/OcrPanel'
import { AiSuggestionPanel } from '../../components/workspace/AiSuggestionPanel'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input, Textarea } from '../../components/ui/Input'
import { useToast } from '../../components/ui/Toast'
import { ANOMALY_SEVERITY_COLORS, ANOMALY_TYPE_LABELS } from '../../lib/constants'


export const ModerationView: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const answerId = Number(id || 814)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast, errorToast } = useToast()

  const [decision, setDecision] = useState<'confirmed' | 'overridden'>('overridden')
  const [moderatedMarks, setModeratedMarks] = useState<string>('')
  const [reason, setReason] = useState<string>('')

  const { data: answer, isLoading } = useQuery({
    queryKey: ['answerDetail', answerId],
    queryFn: () => apiClient.getAnswerDetail(answerId),
  })

  // Set default moderated marks when answer is loaded
  React.useEffect(() => {
    if (answer) {
      setModeratedMarks(
        answer.moderation?.moderated_marks !== undefined
          ? String(answer.moderation.moderated_marks)
          : String(answer.ai.latest?.suggested_marks ?? answer.final_marks ?? 0)
      )
      if (answer.moderation?.reason) {
        setReason(answer.moderation.reason)
      }
    }
  }, [answer])

  const submitModerationMutation = useMutation({
    mutationFn: () =>
      apiClient.submitModeration(answerId, {
        decision,
        moderated_marks: parseFloat(moderatedMarks) || 0,
        reason,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['answerDetail', answerId] })
      queryClient.invalidateQueries({ queryKey: ['moderationQueue'] })
      queryClient.invalidateQueries({ queryKey: ['anomalies'] })
      toast('Moderation decision finalized and anomalies resolved', 'success')
      navigate('/moderator')
    },
    onError: err => errorToast(err),
  })

  if (isLoading || !answer) {
    return (
      <div className="flex h-[70vh] items-center justify-center text-slate-500 text-xs">
        Loading moderation review...
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Link to="/moderator" className="text-xs text-indigo-600 hover:underline">
              ← Back to Moderation Queue
            </Link>
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-1">
            Moderation Review: Question {answer.question.question_number} ({answer.anon_code})
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Inspect handwriting evidence, OCR extraction, AI suggestions, and examiner scores side-by-side.
          </p>
        </div>
      </div>

      {/* Flagged Anomalies Banner */}
      {answer.anomalies && answer.anomalies.length > 0 && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200">
          <h4 className="text-xs font-bold text-rose-900 uppercase tracking-wider mb-2">
            Flagged Anomalies for this Answer ({answer.anomalies.length})
          </h4>
          <div className="space-y-2">
            {answer.anomalies.map(an => {
              const style = ANOMALY_SEVERITY_COLORS[an.severity]
              return (
                <div
                  key={an.id}
                  className="p-3 bg-white rounded-lg border border-rose-100 flex items-start justify-between text-xs"
                >
                  <div>
                    <div className="flex items-center space-x-2">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${style.bg} ${style.text} ${style.border}`}
                      >
                        {ANOMALY_TYPE_LABELS[an.type] || an.type}
                      </span>
                      <span className="font-semibold text-slate-900">{an.note}</span>
                    </div>
                    {an.details && (
                      <div className="mt-1 text-slate-500 text-[11px] font-mono">
                        {JSON.stringify(an.details)}
                      </div>
                    )}
                  </div>
                  <span className="text-[11px] font-bold uppercase text-slate-400">
                    Status: {an.status}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Evidence Comparison Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Scanned Image (5 cols) */}
        <div className="lg:col-span-5 h-[650px]">
          <PageViewer pages={answer.pages} />
        </div>

        {/* Right: Rubric, OCR, AI & Moderation Decision (7 cols) */}
        <div className="lg:col-span-7 space-y-4 max-h-[700px] overflow-y-auto pr-1">
          <RubricPanel
            questionNumber={answer.question.question_number}
            questionText={answer.question.text}
            maxMarks={answer.question.max_marks}
            evaluationMode={answer.question.evaluation_mode}
            rubric={answer.rubric}
          />

          <OcrPanel
            ocr={answer.ocr}
            onSaveText={async () => {}}
            readOnly={true}
          />

          {/* Examiner vs AI Comparison Box */}
          <Card title="Marks Comparison">
            <div className="grid grid-cols-2 gap-4 text-center">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-xs font-semibold text-slate-500 uppercase block">
                  Examiner Awarded
                </span>
                <span className="text-2xl font-black text-slate-900 mt-1 block">
                  {answer.evaluation?.marks_awarded ?? answer.final_marks ?? '—'} / {answer.question.max_marks}
                </span>
                <span className="text-[11px] text-slate-500 mt-0.5 block">
                  By {answer.evaluation?.examiner?.full_name || 'Examiner'} ({answer.evaluation?.source || 'manual'})
                </span>
                {answer.evaluation?.comment && (
                  <p className="text-xs text-slate-600 mt-2 italic">
                    "{answer.evaluation.comment}"
                  </p>
                )}
              </div>

              <div className="p-3 rounded-xl bg-indigo-50 border border-indigo-100">
                <span className="text-xs font-semibold text-indigo-700 uppercase block">
                  AI Suggested
                </span>
                <span className="text-2xl font-black text-indigo-950 mt-1 block">
                  {answer.ai.latest?.suggested_marks ?? '—'} / {answer.question.max_marks}
                </span>
                <span className="text-[11px] text-indigo-600 mt-0.5 block">
                  Confidence: {Math.round((answer.ai.latest?.confidence ?? 0) * 100)}%
                </span>
              </div>
            </div>
          </Card>

          <AiSuggestionPanel
            status={answer.ai.status}
            aiEvaluation={answer.ai.latest}
            onRunAi={async () => {}}
          />

          {/* Moderation Decision Form */}
          <Card
            title="Moderator Final Decision"
            subtitle="Confirm the examiner marks or override with written justification (MD2)"
          >
            <form
              onSubmit={e => {
                e.preventDefault()
                submitModerationMutation.mutate()
              }}
              className="space-y-4"
            >
              <div className="grid grid-cols-2 gap-2 p-1 bg-slate-100 rounded-lg">
                <button
                  type="button"
                  onClick={() => {
                    setDecision('confirmed')
                    setModeratedMarks(String(answer.evaluation?.marks_awarded ?? answer.final_marks ?? 0))
                  }}
                  className={`py-2 text-xs font-bold rounded-md cursor-pointer transition-all ${
                    decision === 'confirmed'
                      ? 'bg-white text-emerald-700 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  ✓ Confirm Examiner Marks
                </button>
                <button
                  type="button"
                  onClick={() => setDecision('overridden')}
                  className={`py-2 text-xs font-bold rounded-md cursor-pointer transition-all ${
                    decision === 'overridden'
                      ? 'bg-white text-indigo-700 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  ✎ Override Marks
                </button>
              </div>

              <Input
                label={`Final Moderated Marks (Max ${answer.question.max_marks})`}
                type="number"
                step="0.5"
                min="0"
                max={answer.question.max_marks}
                required
                value={moderatedMarks}
                onChange={e => setModeratedMarks(e.target.value)}
              />

              <Textarea
                label="Justification Reason (Mandatory for overrides)"
                rows={3}
                required={decision === 'overridden'}
                value={reason}
                onChange={e => setReason(e.target.value)}
                placeholder="Explain the reason for confirming or modifying examiner marks based on rubric and scan evidence..."
              />

              <Button
                variant="primary"
                className="w-full"
                type="submit"
                isLoading={submitModerationMutation.isPending}
              >
                Finalize Moderation Decision
              </Button>
            </form>
          </Card>
        </div>
      </div>
    </div>
  )
}
