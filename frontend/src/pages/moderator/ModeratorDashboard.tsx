import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/ui/Table'
import { ANOMALY_SEVERITY_COLORS, ANOMALY_TYPE_LABELS, type AnomalyType } from '../../lib/constants'


export const ModeratorDashboard: React.FC = () => {
  const [selectedType, setSelectedType] = useState<string>('all')

  const { data: exams = [] } = useQuery({
    queryKey: ['exams'],
    queryFn: () => apiClient.getExams(),
  })
  
  const activeExam = exams.find((e) => e.status === 'moderation') || exams[0]
  const examId = activeExam?.id || 1

  // Poll moderation queue every 30s per frontend-plan.md §5
  const { data: queueData, isLoading } = useQuery({
    queryKey: ['moderationQueue', examId],
    queryFn: () => apiClient.getModerationQueue(examId),
    refetchInterval: 30000,
    refetchIntervalInBackground: false,
    enabled: !!activeExam,
  })

  const { data: anomaliesData } = useQuery({
    queryKey: ['anomalies', examId],
    queryFn: () => apiClient.getAnomalies(examId),
    enabled: !!activeExam,
  })

  const items = queueData?.items || []
  const filtered =
    selectedType === 'all'
      ? items
      : items.filter(it => it.anomalies.some(an => an.type === selectedType))

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Moderation & Quality Review</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Resolve statistical anomalies, unchecked answers, and significant examiner deviations
          </p>
        </div>
      </div>

      {/* Severity & Anomaly Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="!p-4 border-rose-200 bg-rose-50/20">
          <span className="text-[11px] font-bold text-rose-800 uppercase tracking-wider">
            High Severity Flagged
          </span>
          <div className="text-2xl font-black text-rose-700 mt-1">
            {anomaliesData?.items.filter(a => a.severity === 'high' && a.status === 'open').length ?? 0}
          </div>
          <span className="text-[11px] text-rose-600 mt-1 block">Requires moderator decision</span>
        </Card>

        <Card className="!p-4 border-amber-200 bg-amber-50/20">
          <span className="text-[11px] font-bold text-amber-800 uppercase tracking-wider">
            Medium Severity Deviations
          </span>
          <div className="text-2xl font-black text-amber-700 mt-1">
            {anomaliesData?.items.filter(a => a.severity === 'medium' && a.status === 'open').length ?? 0}
          </div>
          <span className="text-[11px] text-amber-600 mt-1 block">Statistical review hints</span>
        </Card>

        <Card className="!p-4">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Resolved Anomalies
          </span>
          <div className="text-2xl font-black text-emerald-600 mt-1">
            {anomaliesData?.items.filter(a => a.status === 'resolved').length ?? 0}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">Confirmed or overridden</span>
        </Card>
      </div>

      {/* Filter Row */}
      <div className="flex items-center space-x-2 bg-white p-3.5 rounded-xl border border-slate-200 overflow-x-auto">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide mr-2">
          Anomaly Filter:
        </span>
        <button
          onClick={() => setSelectedType('all')}
          className={`px-3 py-1 rounded-lg text-xs font-medium cursor-pointer ${
            selectedType === 'all'
              ? 'bg-indigo-600 text-white'
              : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
          }`}
        >
          All Flags ({items.length})
        </button>
        {['AI_DISAGREEMENT', 'UNCHECKED_ANSWER', 'EXAMINER_DEVIATION'].map(type => (
          <button
            key={type}
            onClick={() => setSelectedType(type)}
            className={`px-3 py-1 rounded-lg text-xs font-medium cursor-pointer ${
              selectedType === type
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            {ANOMALY_TYPE_LABELS[type as AnomalyType] || type}
          </button>
        ))}
      </div>

      {/* Moderation Queue Table */}
      <Card
        title="Moderation Review Queue"
        subtitle="Sorted by severity. Overriding marks requires written justification."
      >
        {isLoading ? (
          <div className="p-8 text-center text-slate-400 text-xs">Loading moderation queue...</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs">No answers currently flagged for moderation.</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Question</TableHead>
                <TableHead>Anon Code</TableHead>
                <TableHead>Examiner</TableHead>
                <TableHead>Examiner Marks</TableHead>
                <TableHead>AI Suggestion</TableHead>
                <TableHead>Flagged Anomalies</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map(item => (
                <TableRow key={item.answer_id}>
                  <TableCell className="font-bold text-slate-900">
                    Q{item.question_number}
                  </TableCell>
                  <TableCell className="font-mono font-bold text-indigo-600">
                    {item.anon_code}
                  </TableCell>
                  <TableCell className="text-xs text-slate-700">
                    {item.examiner?.full_name || 'Assigned Examiner'}
                  </TableCell>
                  <TableCell className="font-bold font-mono text-xs text-slate-900">
                    {item.marks} pts
                  </TableCell>
                  <TableCell className="font-mono text-xs text-indigo-700">
                    {item.ai_suggested_marks !== null ? `${item.ai_suggested_marks} pts` : '—'}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {item.anomalies.map((an, i) => {
                        const style = ANOMALY_SEVERITY_COLORS[an.severity]
                        return (
                          <span
                            key={i}
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${style.bg} ${style.text} ${style.border}`}
                          >
                            {ANOMALY_TYPE_LABELS[an.type] || an.type} ({an.severity})
                          </span>
                        )
                      })}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <Link to={`/moderator/answers/${item.answer_id}`}>
                      <Button size="sm" variant="primary">
                        Review & Decide
                      </Button>
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>
    </div>
  )
}
