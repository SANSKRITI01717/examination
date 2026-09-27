import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'

export const Processing: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const examId = Number(id)
  const queryClient = useQueryClient()
  const { toast, errorToast } = useToast()

  // Polling 10s per frontend-plan.md §5
  const { data: status, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['processingStatus', examId],
    queryFn: () => apiClient.getProcessingStatus(examId),
    refetchInterval: 10000,
    refetchIntervalInBackground: false,
  })

  const batchOcrMutation = useMutation({
    mutationFn: () => apiClient.runBatchOcr(examId),
    onSuccess: res => {
      queryClient.invalidateQueries({ queryKey: ['processingStatus', examId] })
      toast(`Queued OCR processing for ${res.queued} answer scripts`, 'success')
    },
    onError: err => errorToast(err),
  })

  const batchAiMutation = useMutation({
    mutationFn: () => apiClient.runBatchAi(examId),
    onSuccess: res => {
      queryClient.invalidateQueries({ queryKey: ['processingStatus', examId] })
      toast(`Queued AI evaluation for ${res.queued} answer scripts`, 'success')
    },
    onError: err => errorToast(err),
  })

  const detectAnomaliesMutation = useMutation({
    mutationFn: () => apiClient.detectAnomalies(examId),
    onSuccess: res => {
      queryClient.invalidateQueries({ queryKey: ['processingStatus', examId] })
      toast(`Triggered anomaly detection. Found ${res.new_anomalies} new anomalies.`, 'success')
    },
    onError: err => errorToast(err),
  })

  const ocrTotal = status ? status.ocr.pending + status.ocr.processing + status.ocr.done + status.ocr.failed : 0
  const ocrDonePct = ocrTotal > 0 ? Math.round((status!.ocr.done / ocrTotal) * 100) : 0

  const markingTotal = status ? status.marking.pending + status.marking.marked + status.marking.flagged + status.marking.moderated : 0
  const markingDonePct = markingTotal > 0 ? Math.round(((status!.marking.marked + status!.marking.moderated) / markingTotal) * 100) : 0

  return (
    <div className="space-y-6">
      {/* Top Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs text-slate-500 mb-1">
            <Link to={`/admin/exams/${examId}`} className="hover:text-indigo-600">
              ← Back to Exam Management
            </Link>
            <span>/</span>
            <span>Exam #{examId}</span>
          </div>
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-bold text-slate-900">Digitization & Marking Pipeline</h2>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className={`w-2 h-2 rounded-full mr-1.5 bg-emerald-500 ${isFetching ? 'animate-ping' : ''}`} />
              Auto-refreshing (10s)
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Trigger batch OCR extraction (O1) and batch AI rubric evaluations. Counters poll automatically.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => refetch()}
            isLoading={isFetching && !batchOcrMutation.isPending && !batchAiMutation.isPending}
            title="Refresh counters immediately"
          >
            ↻ Refresh
          </Button>
          <Button
            variant="outline"
            onClick={() => batchOcrMutation.mutate()}
            isLoading={batchOcrMutation.isPending}
          >
            ▶ Run Batch OCR
          </Button>
          <Button
            variant="primary"
            onClick={() => batchAiMutation.mutate()}
            isLoading={batchAiMutation.isPending}
          >
            ★ Run Batch AI Evaluation
          </Button>
          <Button
            variant="secondary"
            onClick={() => detectAnomaliesMutation.mutate()}
            isLoading={detectAnomaliesMutation.isPending}
          >
            Run Anomaly Detection
          </Button>
        </div>
      </div>

      {/* Low-confidence Verification Alert Banner */}
      {status && status.review_required > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 shadow-xs">
          <div className="flex items-center space-x-3">
            <span className="p-2 bg-amber-100 text-amber-800 rounded-lg text-lg">⚠</span>
            <div>
              <h4 className="text-sm font-bold text-amber-900">
                {status.review_required} Answer Script{status.review_required > 1 ? 's' : ''} Require Human OCR Verification
              </h4>
              <p className="text-xs text-amber-800 mt-0.5">
                Handwriting recognition confidence fell below threshold. Examiners must verify or correct text before accepting AI marks.
              </p>
            </div>
          </div>
          <Link to={`/examiner/exams/${examId}/answers`}>
            <Button size="sm" variant="secondary" className="bg-white border-amber-300 text-amber-900 hover:bg-amber-100 whitespace-nowrap">
              Review Low-Confidence Scripts →
            </Button>
          </Link>
        </div>
      )}

      {/* Main Status Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* OCR Status Box */}
        <Card title="OCR Digitization">
          <div className="space-y-3 mt-1">
            <div>
              <div className="flex justify-between text-xs text-slate-600 mb-1">
                <span>Progress:</span>
                <span className="font-bold">{ocrDonePct}%</span>
              </div>
              <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${ocrDonePct}%` }}
                />
              </div>
            </div>

            <div className="space-y-1.5 text-xs pt-1">
              <div className="flex justify-between p-2 bg-slate-50 rounded border border-slate-100">
                <span className="text-slate-600">Pending Digitization:</span>
                <span className="font-bold font-mono text-slate-800">{status?.ocr.pending ?? 0}</span>
              </div>
              <div className="flex justify-between p-2 bg-blue-50 text-blue-800 rounded border border-blue-100">
                <span className="font-medium">In Processing:</span>
                <span className="font-bold font-mono">{status?.ocr.processing ?? 0}</span>
              </div>
              <div className="flex justify-between p-2 bg-emerald-50 text-emerald-800 rounded border border-emerald-100">
                <span className="font-medium">Digitized (Done):</span>
                <span className="font-bold font-mono">{status?.ocr.done ?? 0}</span>
              </div>
              <div className="flex justify-between p-2 bg-rose-50 text-rose-800 rounded border border-rose-100">
                <span className="font-medium">Failed:</span>
                <span className="font-bold font-mono">{status?.ocr.failed ?? 0}</span>
              </div>
            </div>
          </div>
        </Card>

        {/* AI Evaluation Box */}
        <Card title="AI Rubric Evaluation">
          <div className="space-y-1.5 mt-2 text-xs">
            <div className="flex justify-between p-2 bg-slate-50 rounded border border-slate-100">
              <span className="text-slate-600">Not Requested:</span>
              <span className="font-bold font-mono text-slate-800">{status?.ai.not_requested ?? 0}</span>
            </div>
            <div className="flex justify-between p-2 bg-slate-50 rounded border border-slate-100">
              <span className="text-slate-600">Pending Queue:</span>
              <span className="font-bold font-mono text-slate-800">{status?.ai.pending ?? 0}</span>
            </div>
            <div className="flex justify-between p-2 bg-blue-50 text-blue-800 rounded border border-blue-100">
              <span className="font-medium">Evaluating (LLM):</span>
              <span className="font-bold font-mono">{status?.ai.processing ?? 0}</span>
            </div>
            <div className="flex justify-between p-2 bg-indigo-50 text-indigo-800 rounded border border-indigo-100">
              <span className="font-medium">Suggestions Ready:</span>
              <span className="font-bold font-mono">{status?.ai.done ?? 0}</span>
            </div>
            <div className="flex justify-between p-2 bg-rose-50 text-rose-800 rounded border border-rose-100">
              <span className="font-medium">Failed:</span>
              <span className="font-bold font-mono">{status?.ai.failed ?? 0}</span>
            </div>
          </div>
        </Card>

        {/* OCR Verification Review Box */}
        <Card title="Handwriting Verification">
          <div className="flex flex-col items-center justify-center text-center py-4 h-full">
            <span className="text-4xl font-black text-amber-600 font-mono">
              {status?.review_required ?? 0}
            </span>
            <p className="text-xs font-semibold text-slate-800 mt-2">
              Low Confidence Answers
            </p>
            <p className="text-[11px] text-slate-500 mt-1 max-w-[200px]">
              Flagged by 3-rule confidence heuristics for human inspection before marking
            </p>
            <Link to={`/examiner/exams/${examId}/answers`} className="mt-3">
              <span className="text-xs text-indigo-600 font-semibold hover:underline">
                View Queue →
              </span>
            </Link>
          </div>
        </Card>

        {/* Marking Status Box */}
        <Card title="Marking Progress">
          <div className="space-y-3 mt-1">
            <div>
              <div className="flex justify-between text-xs text-slate-600 mb-1">
                <span>Completed:</span>
                <span className="font-bold">{markingDonePct}%</span>
              </div>
              <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-indigo-600 h-full rounded-full transition-all duration-500"
                  style={{ width: `${markingDonePct}%` }}
                />
              </div>
            </div>

            <div className="space-y-1.5 text-xs pt-1">
              <div className="flex justify-between p-2 bg-slate-50 rounded border border-slate-100">
                <span className="text-slate-600">Pending Marking:</span>
                <span className="font-bold font-mono text-slate-800">{status?.marking.pending ?? 0}</span>
              </div>
              <div className="flex justify-between p-2 bg-emerald-50 text-emerald-800 rounded border border-emerald-100">
                <span className="font-medium">Marked by Examiner:</span>
                <span className="font-bold font-mono">{status?.marking.marked ?? 0}</span>
              </div>
              <div className="flex justify-between p-2 bg-rose-50 text-rose-800 rounded border border-rose-100">
                <span className="font-medium">Flagged Anomalies:</span>
                <span className="font-bold font-mono">{status?.marking.flagged ?? 0}</span>
              </div>
              <div className="flex justify-between p-2 bg-purple-50 text-purple-800 rounded border border-purple-100">
                <span className="font-medium">Moderated:</span>
                <span className="font-bold font-mono">{status?.marking.moderated ?? 0}</span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {isLoading && (
        <div className="p-8 text-center text-slate-400 text-xs">
          Loading pipeline status counters...
        </div>
      )}
    </div>
  )
}
