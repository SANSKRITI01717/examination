import React from 'react'
import type { Rubric, EvaluationMode } from '../../api/types'
import { Badge } from '../ui/Badge'

interface RubricPanelProps {
  questionNumber: string
  questionText: string
  maxMarks: number
  evaluationMode: EvaluationMode
  rubric: Rubric
}

export const RubricPanel: React.FC<RubricPanelProps> = ({
  questionNumber,
  questionText,
  maxMarks,
  evaluationMode,
  rubric,
}) => {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center space-x-2">
          <span className="px-2 py-0.5 rounded-md bg-indigo-100 text-indigo-800 text-xs font-bold uppercase tracking-wider">
            Question {questionNumber}
          </span>
          <Badge variant={evaluationMode === 'reference_grounded' ? 'purple' : 'default'}>
            {evaluationMode === 'reference_grounded' ? 'Reference-grounded' : 'Standard'}
          </Badge>
        </div>
        <div className="text-right flex-shrink-0">
          <span className="text-xs text-slate-500 font-medium">Max Marks:</span>{' '}
          <span className="text-sm font-bold text-slate-900">{maxMarks}</span>
        </div>
      </div>

      <p className="text-sm font-medium text-slate-800 mb-3 leading-relaxed">{questionText}</p>

      {/* Criteria Breakdown */}
      <div className="border-t border-slate-100 pt-3">
        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
          Rubric Criteria
        </h4>
        <div className="space-y-1.5">
          {rubric?.criteria?.map(c => (
            <div
              key={c.id}
              className="flex items-start justify-between text-xs p-2 rounded-lg bg-slate-50 border border-slate-100"
            >
              <div className="pr-2">
                <span className="font-semibold text-slate-800">{c.name}:</span>{' '}
                <span className="text-slate-600">{c.description || 'Graded by rubric specification'}</span>
              </div>
              <span className="font-bold text-slate-700 bg-white px-2 py-0.5 rounded border border-slate-200 flex-shrink-0">
                {c.max_marks} pts
              </span>
            </div>
          ))}
        </div>

        {rubric?.guidance && (
          <div className="mt-2 text-xs text-slate-500 italic bg-amber-50/50 p-2 rounded border border-amber-100/60">
            Guidance: {rubric.guidance}
          </div>
        )}
      </div>
    </div>
  )
}
