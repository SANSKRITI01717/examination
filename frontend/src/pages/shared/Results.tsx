import React, { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { Modal } from '../../components/ui/Modal'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/ui/Table'
import { useToast } from '../../components/ui/Toast'
import type { ResultDetail } from '../../api/types'

export const Results: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const examId = Number(id || 1)
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const { toast, errorToast } = useToast()

  const [breakdownDetail, setBreakdownDetail] = useState<ResultDetail | null>(null)
  const [isBreakdownOpen, setIsBreakdownOpen] = useState<boolean>(false)

  const { data: resultsData, isLoading } = useQuery({
    queryKey: ['results', examId],
    queryFn: () => apiClient.getResults(examId),
  })

  const computeMutation = useMutation({
    mutationFn: () => apiClient.computeResults(examId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['results', examId] })
      toast('Results computed from final human marks', 'success')
    },
    onError: err => errorToast(err),
  })

  const publishMutation = useMutation({
    mutationFn: () => apiClient.publishResults(examId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['results', examId] })
      queryClient.invalidateQueries({ queryKey: ['exams'] })
      toast('Examination results officially published', 'success')
    },
    onError: err => errorToast(err),
  })

  const handleOpenBreakdown = async (resultId: number) => {
    setIsBreakdownOpen(true)
    try {
      const detail = await apiClient.getResultDetail(resultId)
      setBreakdownDetail(detail)
    } catch (err) {
      errorToast(err)
    }
  }

  const items = resultsData?.items || []
  const stats = resultsData?.stats

  const isAdmin = user?.role === 'admin'

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Examination Results & Publishing</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Totals derived strictly from human-authorized marks. View score breakdowns and publish status.
          </p>
        </div>

        {isAdmin && (
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => computeMutation.mutate()}
              isLoading={computeMutation.isPending}
            >
              ⟳ Re-Compute Results
            </Button>
            <Button
              variant="success"
              size="sm"
              onClick={() => publishMutation.mutate()}
              isLoading={publishMutation.isPending}
            >
              ✓ Publish Results
            </Button>
          </div>
        )}
      </div>

      {/* Stats Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <Card className="!p-4">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Mean Score
          </span>
          <div className="text-2xl font-black text-slate-900 mt-1 font-mono">
            {stats?.mean?.toFixed(2) ?? '—'}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">Class average</span>
        </Card>

        <Card className="!p-4">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Median Score
          </span>
          <div className="text-2xl font-black text-indigo-600 mt-1 font-mono">
            {stats?.median?.toFixed(2) ?? '—'}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">50th percentile</span>
        </Card>

        <Card className="!p-4">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Pass Rate
          </span>
          <div className="text-2xl font-black text-emerald-600 mt-1 font-mono">
            {stats?.pass_rate ?? 100}%
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">Candidates passing</span>
        </Card>

        <Card className="!p-4">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Min Score
          </span>
          <div className="text-2xl font-black text-rose-600 mt-1 font-mono">
            {stats?.min?.toFixed(1) ?? '—'}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">Lowest mark</span>
        </Card>

        <Card className="!p-4">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Max Score
          </span>
          <div className="text-2xl font-black text-emerald-600 mt-1 font-mono">
            {stats?.max?.toFixed(1) ?? '—'}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">Top student score</span>
        </Card>
      </div>

      {/* Results Table */}
      <Card
        title="Student Performance Table"
        subtitle="Click any student row to view question-by-question breakdown (RS3)"
      >
        {isLoading ? (
          <div className="p-8 text-center text-slate-400 text-xs">Loading results...</div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs">No results computed yet.</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{isAdmin ? 'Candidate (Roll No)' : 'Candidate (Anon Code)'}</TableHead>
                <TableHead>Total Marks</TableHead>
                <TableHead>Max Marks</TableHead>
                <TableHead>Percentage</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map(res => {
                const studentName = 'full_name' in res.student ? res.student.full_name : ''
                const studentRoll = 'roll_number' in res.student ? res.student.roll_number : ''
                const anonCode = 'anon_code' in res.student ? res.student.anon_code : `S-041${res.id}`

                return (
                  <TableRow
                    key={res.id}
                    onClick={() => handleOpenBreakdown(res.id)}
                  >
                    <TableCell>
                      {isAdmin ? (
                        <div>
                          <span className="font-semibold text-slate-900 block">{studentName}</span>
                          <span className="text-xs text-slate-500 font-mono">{studentRoll}</span>
                        </div>
                      ) : (
                        <span className="font-mono font-bold text-indigo-600">{anonCode}</span>
                      )}
                    </TableCell>
                    <TableCell className="font-mono font-bold text-slate-900">
                      {res.total_marks.toFixed(1)}
                    </TableCell>
                    <TableCell className="font-mono text-slate-500">{res.max_marks}</TableCell>
                    <TableCell className="font-bold text-indigo-600">
                      {res.percentage.toFixed(1)}%
                    </TableCell>
                    <TableCell>
                      <Badge variant={res.status === 'published' ? 'success' : 'warning'}>
                        {res.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={e => {
                          e.stopPropagation()
                          handleOpenBreakdown(res.id)
                        }}
                      >
                        Breakdown ➔
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* Per-Question Breakdown Modal (RS3) */}
      <Modal
        isOpen={isBreakdownOpen}
        onClose={() => setIsBreakdownOpen(false)}
        title="Student Marks Breakdown"
      >
        {breakdownDetail ? (
          <div className="space-y-4">
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 flex justify-between items-center">
              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase block">
                  Final Aggregate
                </span>
                <span className="text-2xl font-black text-slate-900 mt-1 block">
                  {breakdownDetail.result.total_marks} / {breakdownDetail.result.max_marks}{' '}
                  <span className="text-sm text-indigo-600">
                    ({breakdownDetail.result.percentage.toFixed(1)}%)
                  </span>
                </span>
              </div>
              <Badge variant={breakdownDetail.result.status === 'published' ? 'success' : 'warning'}>
                {breakdownDetail.result.status}
              </Badge>
            </div>

            <div>
              <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                Question Scores & Final Source
              </h5>
              <div className="space-y-2">
                {breakdownDetail.breakdown.map((q, i) => (
                  <div
                    key={i}
                    className="p-3 bg-white rounded-lg border border-slate-200 flex items-center justify-between text-xs"
                  >
                    <div>
                      <span className="font-bold text-slate-900 block text-sm">
                        Question {q.question_number}
                      </span>
                      <span className="text-slate-500">
                        Final authority source:{' '}
                        <strong className="capitalize text-slate-700">{q.final_source}</strong>
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-base font-bold font-mono text-indigo-600">
                        {q.marks} / {q.max_marks} pts
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="p-8 text-center text-slate-400 text-xs">Loading breakdown...</div>
        )}
      </Modal>
    </div>
  )
}
