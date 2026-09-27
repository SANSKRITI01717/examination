import React, { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Histogram } from '../../components/charts/Histogram'
import { ExaminerMeanChart } from '../../components/charts/ExaminerMeanChart'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/ui/Table'

export const Analytics: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const examId = Number(id || 1)

  const [selectedQuestionId, setSelectedQuestionId] = useState<number | null>(null)

  const { data: overview } = useQuery({
    queryKey: ['analyticsOverview', examId],
    queryFn: () => apiClient.getAnalyticsOverview(examId),
  })

  const { data: examiners = [] } = useQuery({
    queryKey: ['examinerAnalytics', examId],
    queryFn: () => apiClient.getExaminerAnalytics(examId),
  })

  const { data: questions = [] } = useQuery({
    queryKey: ['questionAnalytics', examId],
    queryFn: () => apiClient.getQuestionAnalytics(examId),
  })

  React.useEffect(() => {
    if (questions.length > 0 && selectedQuestionId === null) {
      setSelectedQuestionId(questions[0].question_id)
    }
  }, [questions, selectedQuestionId])

  const activeQuestionStats =
    questions.find(q => q.question_id === selectedQuestionId) || questions[0]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Examination Analytics & Baselines</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Statistical quality control, per-question mark distributions, and examiner benchmarking
        </p>
      </div>

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="!p-4">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Total Evaluated
          </span>
          <div className="text-2xl font-black text-slate-900 mt-1">
            {overview?.marked ?? 0}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">
            Of {overview?.answers_total ?? 0} total answers
          </span>
        </Card>

        <Card className="!p-4">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Avg Examiner Speed
          </span>
          <div className="text-2xl font-black text-indigo-600 mt-1 font-mono">
            {overview?.avg_seconds_per_answer ?? 0}s
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">Active seconds per script</span>
        </Card>

        <Card className="!p-4 border-amber-200 bg-amber-50/20">
          <span className="text-[11px] font-bold text-amber-800 uppercase tracking-wider">
            OCR Verification Rate
          </span>
          <div className="text-2xl font-black text-amber-700 mt-1">
            {overview?.low_ocr_confidence ?? 0}
          </div>
          <span className="text-[11px] text-amber-600 mt-1 block">Low OCR answers verified</span>
        </Card>

        <Card className="!p-4 border-purple-200 bg-purple-50/20">
          <span className="text-[11px] font-bold text-purple-800 uppercase tracking-wider">
            Moderated Adjustments
          </span>
          <div className="text-2xl font-black text-purple-700 mt-1">
            {overview?.moderated ?? 0}
          </div>
          <span className="text-[11px] text-purple-600 mt-1 block">Overridden by moderator</span>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Question Marks Histogram (AL3) */}
        <Card
          title="Per-Question Marks Distribution"
          subtitle="Histogram of student scores per question"
          action={
            <div className="flex items-center space-x-1">
              {questions.map(q => (
                <button
                  key={q.question_id}
                  onClick={() => setSelectedQuestionId(q.question_id)}
                  className={`px-2.5 py-1 text-xs font-bold rounded-lg cursor-pointer ${
                    activeQuestionStats?.question_id === q.question_id
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  Q{q.question_number}
                </button>
              ))}
            </div>
          }
        >
          {activeQuestionStats && (
            <div>
              <div className="flex items-center justify-between text-xs text-slate-600 mb-3 px-1">
                <span>
                  Mean: <strong>{activeQuestionStats.mean}</strong>
                </span>
                <span>
                  Std Dev: <strong>{activeQuestionStats.sd}</strong>
                </span>
                <span>
                  Min: <strong>{activeQuestionStats.min}</strong>
                </span>
                <span>
                  Max: <strong>{activeQuestionStats.max}</strong>
                </span>
              </div>
              <Histogram
                data={activeQuestionStats.histogram}
                title={`Q${activeQuestionStats.question_number} Score Distribution`}
              />
            </div>
          )}
        </Card>

        {/* Examiner Benchmarking Chart (AL2) */}
        <Card
          title="Examiner Mean vs Global Benchmark"
          subtitle="Assesses whether examiners mark systematically higher or lower than peers"
        >
          <ExaminerMeanChart data={examiners} />
        </Card>
      </div>

      {/* Detailed Examiner Table */}
      <Card title="Examiner Performance & AI Acceptance Breakdown (AL2)">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Examiner</TableHead>
              <TableHead>Marked</TableHead>
              <TableHead>Examiner Mean</TableHead>
              <TableHead>vs Global</TableHead>
              <TableHead>Avg Time</TableHead>
              <TableHead>Accepted AI</TableHead>
              <TableHead>Modified AI</TableHead>
              <TableHead>Manual Marks</TableHead>
              <TableHead>Anomalies</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {examiners.map(ex => (
              <TableRow key={ex.examiner.id}>
                <TableCell className="font-semibold text-slate-900">
                  {ex.examiner.full_name}
                </TableCell>
                <TableCell className="font-bold text-xs">{ex.marked} answers</TableCell>
                <TableCell className="font-mono text-xs">{ex.mean}</TableCell>
                <TableCell
                  className={`font-mono text-xs font-bold ${
                    ex.mean_vs_global < 0 ? 'text-amber-600' : 'text-indigo-600'
                  }`}
                >
                  {ex.mean_vs_global > 0 ? `+${ex.mean_vs_global}` : ex.mean_vs_global}
                </TableCell>
                <TableCell className="font-mono text-xs">{ex.avg_seconds}s</TableCell>
                <TableCell className="text-emerald-700 font-semibold text-xs">
                  {ex.pct_ai_accepted}%
                </TableCell>
                <TableCell className="text-indigo-700 font-semibold text-xs">
                  {ex.pct_ai_modified}%
                </TableCell>
                <TableCell className="text-slate-600 text-xs">{ex.pct_manual}%</TableCell>
                <TableCell className="font-bold text-rose-600 text-xs">{ex.flags}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
