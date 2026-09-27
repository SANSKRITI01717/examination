import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Select } from '../../components/ui/Input'
import { useToast } from '../../components/ui/Toast'

export const Assignments: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const examId = Number(id)
  const { toast, errorToast } = useToast()

  const [strategy, setStrategy] = useState<'by_sheet' | 'by_question'>('by_sheet')
  const [selectedExaminerIds, setSelectedExaminerIds] = useState<number[]>([2])
  const [assignmentResult, setAssignmentResult] = useState<any | null>(null)

  const { data: usersData } = useQuery({
    queryKey: ['users'],
    queryFn: () => apiClient.getUsers(),
  })

  const examiners = usersData?.items.filter(u => u.role === 'examiner') || []

  const assignMutation = useMutation({
    mutationFn: () => apiClient.assignExaminers(examId, selectedExaminerIds, strategy),
    onSuccess: res => {
      setAssignmentResult(res)
      toast(`Successfully assigned ${res.assigned} answer script(s)`, 'success')
    },
    onError: err => errorToast(err),
  })

  const toggleExaminer = (id: number) => {
    if (selectedExaminerIds.includes(id)) {
      setSelectedExaminerIds(selectedExaminerIds.filter(x => x !== id))
    } else {
      setSelectedExaminerIds([...selectedExaminerIds, id])
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center space-x-2">
          <Link to={`/admin/exams/${examId}`} className="text-xs text-indigo-600 hover:underline">
            ← Back to Exam
          </Link>
        </div>
        <h2 className="text-xl font-bold text-slate-900 mt-1">Examiner Assignment</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Distribute unmarked answer scripts across examiners (by complete sheet or per question)
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="Assignment Parameters">
          <form
            onSubmit={e => {
              e.preventDefault()
              assignMutation.mutate()
            }}
            className="space-y-4"
          >
            <Select
              label="Distribution Strategy"
              value={strategy}
              onChange={e => setStrategy(e.target.value as any)}
              options={[
                { value: 'by_sheet', label: 'By Script / Sheet (One examiner marks entire student paper)' },
                { value: 'by_question', label: 'By Question (One examiner marks same question across all scripts)' },
              ]}
            />

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                Available Examiners ({examiners.length})
              </label>
              <div className="space-y-2 border border-slate-200 rounded-lg p-3 bg-slate-50/50">
                {examiners.map(ex => {
                  const isChecked = selectedExaminerIds.includes(ex.id)
                  return (
                    <label
                      key={ex.id}
                      className="flex items-center space-x-3 p-2 rounded-lg bg-white border border-slate-200 cursor-pointer hover:border-indigo-300 transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleExaminer(ex.id)}
                        className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      <div className="text-xs">
                        <span className="font-semibold text-slate-800">{ex.full_name}</span>
                        <span className="text-slate-400 block font-mono">{ex.email}</span>
                      </div>
                    </label>
                  )
                })}
              </div>
            </div>

            <Button
              variant="primary"
              className="w-full"
              type="submit"
              disabled={selectedExaminerIds.length === 0}
              isLoading={assignMutation.isPending}
            >
              Distribute & Assign Scripts
            </Button>
          </form>
        </Card>

        {assignmentResult && (
          <Card title="Assignment Distribution Result">
            <div className="space-y-3">
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-900 text-xs">
                <span className="text-base font-bold block mb-1">
                  ✓ {assignmentResult.assigned} Answers Assigned
                </span>
                Strategy: <strong className="uppercase">{strategy.replace('_', ' ')}</strong>
              </div>

              <div className="space-y-2">
                <h5 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  Workload Breakdown
                </h5>
                {Object.entries(assignmentResult.per_examiner).map(([exId, count]) => {
                  const examiner = examiners.find(e => e.id === Number(exId))
                  return (
                    <div
                      key={exId}
                      className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs"
                    >
                      <span className="font-semibold text-slate-800">
                        {examiner?.full_name || `Examiner #${exId}`}
                      </span>
                      <span className="font-bold font-mono text-indigo-600 bg-white px-2 py-0.5 rounded border border-slate-200">
                        {String(count)} scripts assigned
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
