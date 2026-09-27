import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../ui/Button'

interface QuestionNavProps {
  currentAnswerId: number
  examId: number
  position: number
  total: number
  prevAnswerId: number | null
  nextAnswerId: number | null
  allAnswers?: { id: number; question_number: string; anon_code: string; marking_status: string }[]
  baseRoute?: string // default '/examiner/answers'
}

export const QuestionNav: React.FC<QuestionNavProps> = ({
  currentAnswerId,
  examId,
  position,
  total,
  prevAnswerId,
  nextAnswerId,
  allAnswers = [],
  baseRoute = '/examiner/answers',
}) => {
  const navigate = useNavigate()

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex flex-col h-full">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
        <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
          Script Navigation
        </h4>
        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
          {position} of {total}
        </span>
      </div>

      {/* Answer list items */}
      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
        {allAnswers.map(ans => {
          const isCurrent = ans.id === currentAnswerId
          return (
            <Link
              key={ans.id}
              to={`${baseRoute}/${ans.id}`}
              className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                isCurrent
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-700 hover:bg-slate-100'
              }`}
            >
              <div className="flex items-center space-x-2">
                <span className="font-bold">Q{ans.question_number}</span>
                <span className={isCurrent ? 'text-indigo-200' : 'text-slate-400'}>
                  ({ans.anon_code})
                </span>
              </div>
              <span className="text-xs">
                {ans.marking_status === 'marked' && '✔'}
                {ans.marking_status === 'flagged' && '🚩'}
                {ans.marking_status === 'moderated' && '⚖'}
                {ans.marking_status === 'pending' && '●'}
              </span>
            </Link>
          )
        })}
      </div>

      {/* Prev / Next Buttons */}
      <div className="pt-3 border-t border-slate-100 flex items-center space-x-2 mt-2">
        <Button
          size="sm"
          variant="outline"
          className="flex-1"
          disabled={!prevAnswerId}
          onClick={() => prevAnswerId && navigate(`${baseRoute}/${prevAnswerId}`)}
        >
          ← Prev
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="flex-1"
          disabled={!nextAnswerId}
          onClick={() => nextAnswerId && navigate(`${baseRoute}/${nextAnswerId}`)}
        >
          Next →
        </Button>
      </div>

      <div className="mt-2 text-center">
        <Link
          to={`/examiner/exams/${examId}/answers`}
          className="text-[11px] font-medium text-slate-500 hover:text-indigo-600 transition-colors"
        >
          Back to Answer Queue
        </Link>
      </div>
    </div>
  )
}
