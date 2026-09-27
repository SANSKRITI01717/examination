import React, { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/ui/Table'
import { MARKING_STATUS_COLORS, type MarkingStatus } from '../../lib/constants'

export const AnswerList: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const examId = Number(id || 1)
  const navigate = useNavigate()
  const { user } = useAuth()

  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [ocrReviewOnly, setOcrReviewOnly] = useState<boolean>(false)
  const [assignedToMe, setAssignedToMe] = useState<boolean>(user?.role === 'examiner')
  const [selectedQuestionId, setSelectedQuestionId] = useState<string>('all')
  const [page, setPage] = useState<number>(1)
  const pageSize = 25

  // Fetch Questions for exam to populate question filter
  const { data: questions } = useQuery({
    queryKey: ['questions', examId],
    queryFn: () => apiClient.getQuestions(examId),
    enabled: Boolean(examId),
  })

  // Fetch N1 Answer List
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['answers', examId, statusFilter, ocrReviewOnly, assignedToMe, selectedQuestionId, page],
    queryFn: () =>
      apiClient.getAnswers({
        exam_id: examId,
        question_id: selectedQuestionId === 'all' ? undefined : Number(selectedQuestionId),
        marking_status: statusFilter === 'all' ? undefined : statusFilter,
        assigned_to: assignedToMe ? 'me' : undefined,
        ocr_review_required: ocrReviewOnly ? true : undefined,
        page,
        page_size: pageSize,
      }),
  })

  const answers = data?.items || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / pageSize) || 1
  const firstPending = answers.find(a => a.marking_status === 'pending')

  const resetFilters = () => {
    setStatusFilter('all')
    setOcrReviewOnly(false)
    setSelectedQuestionId('all')
    setPage(1)
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs text-slate-500 mb-1">
            <Link to="/examiner" className="hover:text-indigo-600">
              Examiner Dashboard
            </Link>
            <span>/</span>
            <span>Exam #{examId}</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900">Answer Script Marking Queue</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Blind Marking: Anonymous Student Codes (e.g. S-0417). Student names and roll numbers remain confidential.
          </p>
        </div>

        {firstPending && (
          <Button
            variant="primary"
            onClick={() => navigate(`/examiner/answers/${firstPending.id}`)}
            className="shadow-sm"
          >
            ➔ Open First Pending (Q{firstPending.question_number} • {firstPending.anon_code})
          </Button>
        )}
      </div>

      {/* Filter Controls Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3.5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Status filter pills */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide mr-1">
              Status:
            </span>
            {['all', 'pending', 'marked', 'flagged', 'moderated'].map(st => (
              <button
                key={st}
                onClick={() => {
                  setStatusFilter(st)
                  setPage(1)
                }}
                className={`px-3 py-1 rounded-lg text-xs font-medium capitalize cursor-pointer transition-colors ${
                  statusFilter === st
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          {/* Quick Toggles */}
          <div className="flex flex-wrap items-center gap-4 text-xs font-medium text-slate-700">
            {user?.role === 'examiner' && (
              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={assignedToMe}
                  onChange={e => {
                    setAssignedToMe(e.target.checked)
                    setPage(1)
                  }}
                  className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span>Assigned to me only</span>
              </label>
            )}

            <label className="flex items-center space-x-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={ocrReviewOnly}
                onChange={e => {
                  setOcrReviewOnly(e.target.checked)
                  setPage(1)
                }}
                className="rounded border-slate-300 text-amber-600 focus:ring-amber-500"
              />
              <span className="text-amber-900 font-semibold">⚠ Needs OCR Review</span>
            </label>
          </div>
        </div>

        {/* Second Row: Question Filter & Reset */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-100 text-xs">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-500">Filter Question:</span>
            <select
              value={selectedQuestionId}
              onChange={e => {
                setSelectedQuestionId(e.target.value)
                setPage(1)
              }}
              className="px-2.5 py-1 rounded-lg border border-slate-200 bg-slate-50 text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">All Questions</option>
              {questions?.map(q => (
                <option key={q.id} value={q.id}>
                  Question {q.question_number} ({q.max_marks} marks)
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-3 text-slate-500">
            <span>
              Total results: <strong>{total}</strong> answers
            </span>
            {(statusFilter !== 'all' || ocrReviewOnly || selectedQuestionId !== 'all') && (
              <button
                onClick={resetFilters}
                className="text-xs text-indigo-600 hover:underline cursor-pointer font-medium"
              >
                Reset filters
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Answer List Table Card */}
      <Card title={`Answer Scripts (${total})`}>
        {isLoading ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-solid border-indigo-600 border-r-transparent mb-2"></div>
            <p>Loading candidate answers...</p>
          </div>
        ) : isError ? (
          <div className="p-8 text-center text-rose-600 text-xs">
            <p className="font-semibold">Failed to load answers from server.</p>
            <Button size="sm" variant="outline" onClick={() => refetch()} className="mt-2">
              Retry
            </Button>
          </div>
        ) : answers.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-xs space-y-2">
            <p className="font-semibold text-slate-600">No answer scripts found matching these criteria.</p>
            <p>Try clearing filters or checking other exams.</p>
            <Button size="sm" variant="outline" onClick={resetFilters} className="mt-2">
              Reset Filters
            </Button>
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Question</TableHead>
                  <TableHead>Anon Candidate Code</TableHead>
                  <TableHead>OCR Digitization</TableHead>
                  <TableHead>AI Suggestion</TableHead>
                  <TableHead>Marking Status</TableHead>
                  <TableHead>Awarded Marks</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {answers.map(ans => {
                  const statusStyle =
                    MARKING_STATUS_COLORS[ans.marking_status as MarkingStatus] ||
                    MARKING_STATUS_COLORS.pending

                  return (
                    <TableRow key={ans.id}>
                      <TableCell className="font-bold text-slate-900">
                        Q{ans.question_number}
                      </TableCell>
                      <TableCell className="font-mono font-bold text-indigo-600">
                        {ans.anon_code}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-1.5">
                          <span className="text-xs text-slate-700 capitalize font-medium">
                            {ans.ocr_status}
                          </span>
                          {ans.ocr_review_required && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                              Review needed
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs text-slate-600 capitalize">
                          {ans.ai_status}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${statusStyle.bg} ${statusStyle.text} ${statusStyle.border}`}
                        >
                          {ans.marking_status}
                        </span>
                      </TableCell>
                      <TableCell className="font-bold font-mono text-xs text-slate-900">
                        {ans.final_marks !== null ? `${ans.final_marks} / ${ans.max_marks}` : '—'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Link to={`/examiner/answers/${ans.id}`}>
                          <Button
                            size="sm"
                            variant={ans.marking_status === 'pending' ? 'primary' : 'outline'}
                          >
                            {ans.marking_status === 'pending' ? 'Mark Answer' : 'Open Workspace'}
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-xs text-slate-500">
                <div>
                  Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} scripts
                </div>
                <div className="flex items-center space-x-1.5">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={page <= 1}
                    onClick={() => setPage(p => Math.max(p - 1, 1))}
                  >
                    ← Prev
                  </Button>
                  <span className="px-2 font-mono font-medium">
                    {page} / {totalPages}
                  </span>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={page >= totalPages}
                    onClick={() => setPage(p => Math.min(p + 1, totalPages))}
                  >
                    Next →
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  )
}
