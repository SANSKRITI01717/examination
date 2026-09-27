import React from 'react'
import type { AiEvaluation, AiStatus } from '../../api/types'
import { ConfidenceBadge } from './ConfidenceBadge'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { AI_ASSISTANT_LABEL } from '../../lib/constants'

interface AiSuggestionPanelProps {
  status: AiStatus
  aiEvaluation: AiEvaluation | null
  onRunAi: () => Promise<void>
  isRunningAi?: boolean
}

export const AiSuggestionPanel: React.FC<AiSuggestionPanelProps> = ({
  status,
  aiEvaluation,
  onRunAi,
  isRunningAi = false,
}) => {
  if (status === 'not_requested' && !aiEvaluation) {
    return (
      <div className="bg-indigo-50/40 rounded-xl border border-indigo-100 p-5 text-center">
        <div className="w-10 h-10 mx-auto mb-2 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <h4 className="text-sm font-bold text-indigo-950 mb-1">{AI_ASSISTANT_LABEL}</h4>
        <p className="text-xs text-indigo-700/80 mb-3 max-w-sm mx-auto">
          AI evaluation has not been generated for this answer yet.
        </p>
        <Button size="sm" variant="primary" onClick={onRunAi} isLoading={isRunningAi}>
          Get AI Suggestion
        </Button>
      </div>
    )
  }

  if (status === 'processing' || isRunningAi) {
    return (
      <div className="bg-indigo-50/30 rounded-xl border border-indigo-100 p-6 text-center">
        <div className="inline-block h-6 w-6 animate-spin rounded-full border-3 border-solid border-indigo-600 border-r-transparent mb-2"></div>
        <p className="text-xs font-semibold text-indigo-950">Generating AI Evaluation...</p>
        <p className="text-[11px] text-indigo-600/75 mt-0.5">Evaluating against rubric criteria</p>
      </div>
    )
  }

  if (!aiEvaluation) {
    return null
  }

  return (
    <div className="bg-white rounded-xl border border-indigo-200/80 p-4 shadow-xs relative overflow-hidden">
      {/* Required top non-negotiable branding header */}
      <div className="flex items-center justify-between flex-wrap gap-2 pb-3 border-b border-indigo-50">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 rounded-full bg-indigo-600" />
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-950">
            {AI_ASSISTANT_LABEL}
          </span>
          <Badge variant={aiEvaluation.mode_used === 'reference_grounded' ? 'purple' : 'info'}>
            {aiEvaluation.mode_used === 'reference_grounded' ? 'Ref-Grounded' : 'Standard'}
          </Badge>
        </div>

        <div className="flex items-center space-x-2">
          <ConfidenceBadge confidence={aiEvaluation.confidence} label="Confidence" />
        </div>
      </div>

      {/* Stale or Warning Banner */}
      {aiEvaluation.stale && (
        <div className="my-2.5 p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-xs flex items-center justify-between">
          <span className="text-amber-800 font-medium">
            ⚠ OCR text was modified. Suggestion is out of date.
          </span>
          <Button size="sm" variant="outline" onClick={onRunAi} isLoading={isRunningAi}>
            Re-run AI
          </Button>
        </div>
      )}

      {/* Warnings Chips */}
      {aiEvaluation.warnings && aiEvaluation.warnings.length > 0 && (
        <div className="flex flex-wrap gap-1.5 my-2">
          {aiEvaluation.warnings.map(w => (
            <span
              key={w}
              className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200"
            >
              ⚠ {w}
            </span>
          ))}
        </div>
      )}

      {/* Marks Summary */}
      <div className="my-3 flex items-baseline justify-between bg-indigo-50/40 p-3 rounded-lg border border-indigo-100">
        <div>
          <span className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
            Suggested Marks:
          </span>
          <div className="text-2xl font-black text-indigo-950">
            {aiEvaluation.suggested_marks}{' '}
            <span className="text-sm font-semibold text-slate-400">/ {aiEvaluation.max_marks}</span>
          </div>
        </div>
        <div className="text-right">
          <span className="text-[11px] text-slate-400">Model: {aiEvaluation.model_name}</span>
        </div>
      </div>

      {/* Criteria Breakdown */}
      <div className="space-y-2 mb-3">
        <h5 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
          Criterion Suggestions & Reasoning
        </h5>
        {aiEvaluation.criteria.map(c => (
          <div
            key={c.criterion_id}
            className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-xs"
          >
            <div className="flex items-center justify-between font-semibold text-slate-800 mb-1">
              <span>{c.criterion}</span>
              <span className="text-indigo-700 font-bold bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
                {c.awarded_marks} / {c.max_marks} pts
              </span>
            </div>
            <p className="text-slate-600 leading-relaxed">{c.reason}</p>
          </div>
        ))}
      </div>

      {/* Overall Reasoning */}
      {aiEvaluation.overall_reason && (
        <div className="pt-2 border-t border-slate-100 text-xs text-slate-600">
          <span className="font-semibold text-slate-800">Overall Reasoning:</span>{' '}
          {aiEvaluation.overall_reason}
        </div>
      )}
    </div>
  )
}
