import React, { useState, useEffect, useRef } from 'react'
import type { Rubric, AiEvaluation, Evaluation } from '../../api/types'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'

interface MarkingPanelProps {
  maxMarks: number
  rubric: Rubric
  aiEvaluation: AiEvaluation | null
  existingEvaluation: Evaluation | null
  isOcrVerified: boolean
  ocrReviewRequired: boolean
  onAcceptAi: (aiEvaluationId: number, activeSeconds: number) => Promise<void>
  onSubmitMarks: (data: {
    marks_awarded: number
    criterion_marks?: Record<string, number>
    comment?: string
    source: 'ai_modified' | 'manual'
    ai_evaluation_id?: number
    active_seconds: number
    submit: boolean
  }) => Promise<void>
  isSubmitting?: boolean
  serverError?: string | null
}

export const MarkingPanel: React.FC<MarkingPanelProps> = ({
  maxMarks,
  rubric,
  aiEvaluation,
  existingEvaluation,
  isOcrVerified,
  ocrReviewRequired,
  onAcceptAi,
  onSubmitMarks,
  isSubmitting = false,
  serverError = null,
}) => {
  type Mode = 'accept' | 'modify' | 'manual'
  const [mode, setMode] = useState<Mode>(
    existingEvaluation?.source === 'manual'
      ? 'manual'
      : existingEvaluation?.source === 'ai_modified'
      ? 'modify'
      : 'accept'
  )

  // Criteria marks map for 'modify' mode
  const [criterionScores, setCriterionScores] = useState<Record<string, number>>({})
  // Manual marks for 'manual' mode
  const [manualMarks, setManualMarks] = useState<string>(
    existingEvaluation ? String(existingEvaluation.marks_awarded) : ''
  )
  const [comment, setComment] = useState<string>(existingEvaluation?.comment || '')
  const [validationError, setValidationError] = useState<string | null>(null)

  // Active time tracking (count only while tab is active and visible)
  const [activeSeconds, setActiveSeconds] = useState(0)
  const lastActiveRef = useRef(Date.now())

  useEffect(() => {
    const handleActivity = () => {
      lastActiveRef.current = Date.now()
    }
    window.addEventListener('mousemove', handleActivity)
    window.addEventListener('keydown', handleActivity)

    const interval = setInterval(() => {
      if (document.visibilityState === 'visible' && Date.now() - lastActiveRef.current < 60000) {
        setActiveSeconds(prev => prev + 1)
      }
    }, 1000)

    return () => {
      clearInterval(interval)
      window.removeEventListener('mousemove', handleActivity)
      window.removeEventListener('keydown', handleActivity)
    }
  }, [])

  // Prefill modify criteria when AI evaluation or mode changes
  useEffect(() => {
    if (aiEvaluation?.criteria) {
      const initial: Record<string, number> = {}
      aiEvaluation.criteria.forEach(c => {
        initial[c.criterion_id] = c.awarded_marks
      })
      setCriterionScores(initial)
    } else if (rubric?.criteria) {
      const initial: Record<string, number> = {}
      rubric.criteria.forEach(c => {
        initial[c.id] = existingEvaluation?.criterion_marks?.[c.id] ?? 0
      })
      setCriterionScores(initial)
    }
  }, [aiEvaluation, rubric, existingEvaluation])

  // Calculated sum for modify mode
  const computedModifySum = Object.values(criterionScores).reduce((acc, curr) => acc + (Number(curr) || 0), 0)

  // Accept checks
  const canAccept =
    Boolean(aiEvaluation) &&
    !aiEvaluation?.stale &&
    (!ocrReviewRequired || isOcrVerified)

  const handleAccept = async () => {
    if (!aiEvaluation) return
    setValidationError(null)
    await onAcceptAi(aiEvaluation.id, Math.max(activeSeconds, 1))
  }

  const handleModifySubmit = async () => {
    setValidationError(null)
    if (computedModifySum < 0 || computedModifySum > maxMarks) {
      setValidationError(`Total modified marks (${computedModifySum}) exceeds maximum (${maxMarks})`)
      return
    }
    await onSubmitMarks({
      marks_awarded: computedModifySum,
      criterion_marks: criterionScores,
      comment,
      source: 'ai_modified',
      ai_evaluation_id: aiEvaluation?.id,
      active_seconds: Math.max(activeSeconds, 1),
      submit: true,
    })
  }

  const handleManualSubmit = async () => {
    setValidationError(null)
    const marksNum = parseFloat(manualMarks)
    if (isNaN(marksNum)) {
      setValidationError('Please enter a valid numeric mark')
      return
    }
    if (marksNum < 0 || marksNum > maxMarks) {
      setValidationError(`Marks must be between 0 and ${maxMarks}`)
      return
    }
    await onSubmitMarks({
      marks_awarded: marksNum,
      comment,
      source: 'manual',
      active_seconds: Math.max(activeSeconds, 1),
      submit: true,
    })
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
          Final Human Marking
        </h4>
        <div className="text-[11px] text-slate-500 font-mono">
          Time: {Math.floor(activeSeconds / 60)}m {activeSeconds % 60}s
        </div>
      </div>

      {/* Mode selection buttons */}
      <div className="grid grid-cols-3 gap-1.5 my-3 p-1 bg-slate-100 rounded-lg">
        <button
          type="button"
          onClick={() => setMode('accept')}
          className={`py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer ${
            mode === 'accept'
              ? 'bg-white text-indigo-700 shadow-xs'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          1. Accept AI
        </button>
        <button
          type="button"
          onClick={() => setMode('modify')}
          className={`py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer ${
            mode === 'modify'
              ? 'bg-white text-indigo-700 shadow-xs'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          2. Modify
        </button>
        <button
          type="button"
          onClick={() => setMode('manual')}
          className={`py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer ${
            mode === 'manual'
              ? 'bg-white text-indigo-700 shadow-xs'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          3. Enter Manually
        </button>
      </div>

      {/* Inline Errors */}
      {(validationError || serverError) && (
        <div className="mb-3 p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 font-medium">
          ⚠ {validationError || serverError}
        </div>
      )}

      {/* Accept Mode */}
      {mode === 'accept' && (
        <div className="space-y-3">
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 text-xs">
            <div className="flex justify-between items-center mb-1">
              <span className="font-semibold text-slate-700">AI Suggested Marks:</span>
              <span className="text-base font-bold text-indigo-600">
                {aiEvaluation ? `${aiEvaluation.suggested_marks} / ${maxMarks}` : '—'}
              </span>
            </div>
            <p className="text-slate-500">
              Accepting will finalize the exact AI criterion breakdown and store Dr. Turing as the authoritative human examiner.
            </p>
          </div>

          {!canAccept && (
            <p className="text-xs text-amber-700 font-medium">
              {ocrReviewRequired && !isOcrVerified
                ? '⚠ Low-confidence OCR text must be confirmed before accepting AI recommendation.'
                : '⚠ AI suggestion is missing or stale. Modify marks or re-run AI.'}
            </p>
          )}

          <Button
            variant="primary"
            className="w-full"
            disabled={!canAccept}
            isLoading={isSubmitting}
            onClick={handleAccept}
          >
            ✓ Accept AI Recommendation ({aiEvaluation?.suggested_marks ?? 0} Marks)
          </Button>
        </div>
      )}

      {/* Modify Mode */}
      {mode === 'modify' && (
        <div className="space-y-3">
          <div className="space-y-2">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Adjust Criteria (Auto-sums to total)
            </div>
            {rubric?.criteria?.map(c => {
              const currentVal = criterionScores[c.id] ?? 0
              return (
                <div
                  key={c.id}
                  className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-200"
                >
                  <div className="text-xs font-medium text-slate-800 pr-2 truncate">
                    {c.name} <span className="text-slate-400">(max {c.max_marks})</span>
                  </div>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    max={c.max_marks}
                    value={currentVal}
                    onChange={e => {
                      const val = parseFloat(e.target.value) || 0
                      setCriterionScores(prev => ({ ...prev, [c.id]: Math.min(val, c.max_marks) }))
                    }}
                    className="w-20 px-2 py-1 text-right text-xs font-bold font-mono border border-slate-300 rounded bg-white focus:outline-indigo-500"
                  />
                </div>
              )
            })}
          </div>

          <div className="flex items-center justify-between p-2.5 rounded-lg bg-indigo-50 border border-indigo-100 text-xs font-bold text-indigo-950">
            <span>Computed Total Marks:</span>
            <span className="text-sm">{computedModifySum} / {maxMarks}</span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Examiner Note (Optional)
            </label>
            <input
              type="text"
              value={comment}
              onChange={e => setComment(e.target.value)}
              placeholder="e.g. Partial marks given for clear diagram"
              className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg bg-white"
            />
          </div>

          <Button
            variant="success"
            className="w-full"
            isLoading={isSubmitting}
            onClick={handleModifySubmit}
          >
            Submit Modified Marks ({computedModifySum})
          </Button>
        </div>
      )}

      {/* Manual Mode */}
      {mode === 'manual' && (
        <div className="space-y-3">
          <div>
            <Input
              label={`Total Awarded Marks (0 to ${maxMarks}, step 0.5)`}
              type="number"
              step="0.5"
              min="0"
              max={maxMarks}
              value={manualMarks}
              onChange={e => setManualMarks(e.target.value)}
              placeholder="e.g. 7.5"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Examiner Note / Justification
            </label>
            <input
              type="text"
              value={comment}
              onChange={e => setComment(e.target.value)}
              placeholder="e.g. Hand-marked based on handwriting clarity"
              className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg bg-white"
            />
          </div>

          <Button
            variant="primary"
            className="w-full"
            isLoading={isSubmitting}
            onClick={handleManualSubmit}
          >
            Submit Manual Marks
          </Button>
        </div>
      )}
    </div>
  )
}
