import React from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/ui/Table'
import { EXAM_STATUS_COLORS } from '../../lib/constants'

export const AdminDashboard: React.FC = () => {
  const { data: exams = [], isLoading: examsLoading } = useQuery({
    queryKey: ['exams'],
    queryFn: () => apiClient.getExams(),
  })

  // Poll overview statistics every 15s per frontend-plan.md §5
  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['analyticsOverview', 1],
    queryFn: () => apiClient.getAnalyticsOverview(1),
    refetchInterval: 15000,
    refetchIntervalInBackground: false,
  })

  return (
    <div className="space-y-6">
      {/* Top Welcome / Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Examination Administration</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage examination cycles, answer sheets, OCR digitization and evaluation rules
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Link to="/admin/exams/new">
            <Button variant="primary" size="sm">
              + New Examination
            </Button>
          </Link>
        </div>
      </div>

      {/* Overview Stat Cards (polled 15s) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="!p-4">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Total Answers
          </span>
          <div className="text-2xl font-black text-slate-900 mt-1">
            {overviewLoading ? '...' : overview?.answers_total ?? 0}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">
            {overview?.ocr_done} OCR digitized
          </span>
        </Card>

        <Card className="!p-4">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Evaluated by Humans
          </span>
          <div className="text-2xl font-black text-emerald-600 mt-1">
            {overviewLoading ? '...' : overview?.marked ?? 0}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">
            {overview?.moderated} moderated
          </span>
        </Card>

        <Card className="!p-4 border-amber-200 bg-amber-50/20">
          <span className="text-[11px] font-bold text-amber-700 uppercase tracking-wider">
            Low OCR Confidence
          </span>
          <div className="text-2xl font-black text-amber-700 mt-1">
            {overviewLoading ? '...' : overview?.low_ocr_confidence ?? 0}
          </div>
          <span className="text-[11px] text-amber-600 mt-1 block">
            Requires human verification
          </span>
        </Card>

        <Card className="!p-4 border-rose-200 bg-rose-50/20">
          <span className="text-[11px] font-bold text-rose-700 uppercase tracking-wider">
            Flagged & Unchecked
          </span>
          <div className="text-2xl font-black text-rose-700 mt-1">
            {overviewLoading ? '...' : (overview?.flagged ?? 0) + (overview?.unchecked ?? 0)}
          </div>
          <span className="text-[11px] text-rose-600 mt-1 block">
            {overview?.unchecked} unchecked answers
          </span>
        </Card>
      </div>

      {/* Exams Table */}
      <Card
        title="Examinations"
        subtitle="Manage questions, rubrics, sheets, assignments and processing pipeline"
      >
        {examsLoading ? (
          <div className="p-8 text-center text-slate-500 text-sm">Loading examinations...</div>
        ) : exams.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-sm">No examinations created yet.</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Course</TableHead>
                <TableHead>Exam Title</TableHead>
                <TableHead>Exam Date</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {exams.map(exam => {
                const statusColor = EXAM_STATUS_COLORS[exam.status] || EXAM_STATUS_COLORS.draft
                return (
                  <TableRow key={exam.id}>
                    <TableCell className="font-bold text-slate-900">
                      {exam.course_code}
                    </TableCell>
                    <TableCell className="font-medium text-slate-800">
                      <Link
                        to={`/admin/exams/${exam.id}`}
                        className="hover:text-indigo-600 transition-colors"
                      >
                        {exam.title}
                      </Link>
                    </TableCell>
                    <TableCell className="text-slate-500 text-xs">
                      {exam.exam_date || 'Not scheduled'}
                    </TableCell>
                    <TableCell>
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${statusColor.bg} ${statusColor.text} ${statusColor.border}`}
                      >
                        {exam.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-right space-x-1.5">
                      <Link to={`/admin/exams/${exam.id}`}>
                        <Button size="sm" variant="outline">
                          Setup
                        </Button>
                      </Link>
                      <Link to={`/admin/exams/${exam.id}/questions`}>
                        <Button size="sm" variant="outline">
                          Rubrics
                        </Button>
                      </Link>
                      <Link to={`/admin/exams/${exam.id}/processing`}>
                        <Button size="sm" variant="secondary">
                          Processing
                        </Button>
                      </Link>
                      <Link to={`/exams/${exam.id}/analytics`}>
                        <Button size="sm" variant="ghost">
                          Analytics
                        </Button>
                      </Link>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        )}
      </Card>
    </div>
  )
}
