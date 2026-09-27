import React from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { ProgressBar } from '../../components/charts/ProgressBar'

export const ExaminerDashboard: React.FC = () => {
  const { data: exams = [] } = useQuery({
    queryKey: ['exams'],
    queryFn: () => apiClient.getExams(),
  })

  const activeExam = exams.find((e: any) => e.status === 'evaluation') || exams[0]
  const examId = activeExam?.id || 1

  // Poll examiner workload progress every 30s per frontend-plan.md §5
  const { data: progress } = useQuery({
    queryKey: ['examinerProgress', examId],
    queryFn: () => apiClient.getMyProgress(examId),
    refetchInterval: 30000,
    refetchIntervalInBackground: false,
    enabled: !!activeExam,
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Examiner Marking Portal</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Review student scripts, verify OCR text, and evaluate with AI assistance
          </p>
        </div>
        <Link to="/examiner/answers/812">
          <Button variant="primary" size="md">
            ➔ Resume Marking (Answer #812)
          </Button>
        </Link>
      </div>

      {/* Progress Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="!p-4">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Assigned Scripts
          </span>
          <div className="text-2xl font-black text-slate-900 mt-1">
            {progress?.assigned ?? 6}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">In active exam</span>
        </Card>

        <Card className="!p-4">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Marked Answers
          </span>
          <div className="text-2xl font-black text-emerald-600 mt-1">
            {progress?.marked ?? 4}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">Human decisions submitted</span>
        </Card>

        <Card className="!p-4">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Remaining to Mark
          </span>
          <div className="text-2xl font-black text-indigo-600 mt-1">
            {progress?.remaining ?? 2}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">Pending in queue</span>
        </Card>

        <Card className="!p-4 border-amber-200 bg-amber-50/20">
          <span className="text-[11px] font-bold text-amber-700 uppercase tracking-wider">
            OCR Verification Required
          </span>
          <div className="text-2xl font-black text-amber-700 mt-1">
            {progress?.review_required ?? 1}
          </div>
          <span className="text-[11px] text-amber-600 mt-1 block">Low OCR handwriting</span>
        </Card>
      </div>

      {/* Assigned Exams List */}
      <Card title="My Assigned Examination Papers">
        <div className="space-y-4">
          {exams.map(exam => (
            <div
              key={exam.id}
              className="p-4 rounded-xl border border-slate-200 bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xs"
            >
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-slate-900 text-sm">
                    {exam.course_code}: {exam.title}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-blue-50 text-blue-700 border border-blue-200">
                    {exam.status}
                  </span>
                </div>
                <p className="text-xs text-slate-500">Exam date: {exam.exam_date || 'N/A'}</p>
                <div className="max-w-md pt-1">
                  <ProgressBar
                    label="Completion Progress"
                    current={progress?.marked ?? 4}
                    total={progress?.assigned ?? 6}
                    color="emerald"
                  />
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <Link to={`/examiner/exams/${exam.id}/answers`}>
                  <Button variant="outline" size="sm">
                    Open Answer Queue
                  </Button>
                </Link>
                <Link to="/examiner/answers/812">
                  <Button variant="primary" size="sm">
                    Open Workspace
                  </Button>
                </Link>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
