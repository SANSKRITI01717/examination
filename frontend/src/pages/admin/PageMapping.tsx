import React, { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'

interface MappingItem {
  question_id: number
  question_number: string
  page_start: number
  page_end: number
  is_attempted: boolean
}

export const PageMapping: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const sheetId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast, errorToast } = useToast()

  const [mappings, setMappings] = useState<MappingItem[]>([])

  const { data: sheet } = useQuery({
    queryKey: ['sheetDetail', sheetId],
    queryFn: () => apiClient.getSheetDetail(sheetId),
  })

  const { data: questions = [] } = useQuery({
    queryKey: ['questions', sheet?.exam_id],
    queryFn: () => (sheet ? apiClient.getQuestions(sheet.exam_id) : []),
    enabled: Boolean(sheet?.exam_id),
  })

  // Initialize mappings with default helper: if page_count == question_count, pre-fill one page per question
  useEffect(() => {
    if (questions.length > 0 && sheet) {
      if (sheet.answers && sheet.answers.length > 0) {
        setMappings(
          sheet.answers.map(a => ({
            question_id: a.question_id,
            question_number: a.question_number,
            page_start: a.page_start || 1,
            page_end: a.page_end || 1,
            is_attempted: a.is_attempted,
          }))
        )
      } else {
        const isOneToOne = sheet.page_count === questions.length
        setMappings(
          questions.map((q, idx) => ({
            question_id: q.id,
            question_number: q.question_number,
            page_start: isOneToOne ? idx + 1 : 1,
            page_end: isOneToOne ? idx + 1 : 1,
            is_attempted: true,
          }))
        )
      }
    }
  }, [questions, sheet])

  const saveMappingMutation = useMutation({
    mutationFn: () =>
      apiClient.savePageMapping(
        sheetId,
        mappings.map(m => ({
          question_id: m.question_id,
          page_start: m.page_start,
          page_end: m.page_end,
          is_attempted: m.is_attempted,
        }))
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sheetDetail', sheetId] })
      queryClient.invalidateQueries({ queryKey: ['sheets'] })
      toast('Page mapping saved successfully', 'success')
      navigate(`/admin/exams/${sheet?.exam_id}/sheets`)
    },
    onError: err => errorToast(err),
  })

  const updateMapping = (index: number, updates: Partial<MappingItem>) => {
    const next = [...mappings]
    next[index] = { ...next[index], ...updates }
    setMappings(next)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Link to={`/admin/exams/${sheet?.exam_id}/sheets`} className="text-xs text-indigo-600 hover:underline">
              ← Back to Sheets
            </Link>
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-1">
            Map Pages to Questions — Sheet {sheet?.anon_code}
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Admin page-to-question segmentation. Assign page ranges to each question or mark as unattempted.
          </p>
        </div>

        <Button
          variant="primary"
          onClick={() => saveMappingMutation.mutate()}
          isLoading={saveMappingMutation.isPending}
        >
          Save Page Mapping
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Page Thumbnails */}
        <div className="lg:col-span-1 space-y-3">
          <Card title={`Scanned Pages (${sheet?.pages?.length || 0})`}>
            <div className="space-y-3 max-h-[70vh] overflow-y-auto pr-1">
              {sheet?.pages?.map(p => (
                <div key={p.id} className="border border-slate-200 rounded-xl overflow-hidden bg-slate-900 shadow-xs">
                  <div className="px-3 py-1.5 bg-slate-950 text-white text-xs font-bold flex justify-between">
                    <span>Page {p.page_number}</span>
                  </div>
                  <img
                    src={p.image_url}
                    alt={`Page ${p.page_number}`}
                    className="w-full object-contain max-h-48 bg-slate-800"
                  />
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Right: Question Mapping Form */}
        <div className="lg:col-span-2">
          <Card
            title="Question Page Allocation"
            subtitle="Define which scanned page contains the student's answer for each question"
          >
            <div className="space-y-4">
              {mappings.map((m, idx) => (
                <div
                  key={m.question_id}
                  className={`p-4 rounded-xl border transition-all ${
                    m.is_attempted
                      ? 'bg-white border-slate-200 shadow-xs'
                      : 'bg-slate-50 border-slate-200 opacity-60'
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <span className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-700 font-bold flex items-center justify-center text-sm border border-indigo-100">
                        Q{m.question_number}
                      </span>
                      <span className="font-semibold text-slate-800 text-sm">
                        Question {m.question_number}
                      </span>
                    </div>

                    <label className="flex items-center space-x-2 text-xs font-semibold text-slate-600 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={m.is_attempted}
                        onChange={e => updateMapping(idx, { is_attempted: e.target.checked })}
                        className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span>Attempted by student</span>
                    </label>
                  </div>

                  {m.is_attempted ? (
                    <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-100">
                      <div>
                        <label className="block text-[11px] font-bold text-slate-500 uppercase mb-1">
                          Start Page
                        </label>
                        <select
                          value={m.page_start}
                          onChange={e => updateMapping(idx, { page_start: Number(e.target.value) })}
                          className="w-full px-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white text-slate-800"
                        >
                          {sheet?.pages?.map(p => (
                            <option key={p.id} value={p.page_number}>
                              Page {p.page_number}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-[11px] font-bold text-slate-500 uppercase mb-1">
                          End Page
                        </label>
                        <select
                          value={m.page_end}
                          onChange={e => updateMapping(idx, { page_end: Number(e.target.value) })}
                          className="w-full px-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white text-slate-800"
                        >
                          {sheet?.pages?.map(p => (
                            <option key={p.id} value={p.page_number}>
                              Page {p.page_number}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 italic">
                      Marked as not attempted. System will record 0 marks automatically.
                    </p>
                  )}
                </div>
              ))}

              <div className="flex justify-end pt-3 border-t border-slate-100">
                <Button
                  variant="primary"
                  onClick={() => saveMappingMutation.mutate()}
                  isLoading={saveMappingMutation.isPending}
                >
                  Save & Complete Mapping
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
