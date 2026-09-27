import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input, Select, Textarea } from '../../components/ui/Input'
import { Badge } from '../../components/ui/Badge'
import { Modal } from '../../components/ui/Modal'
import { useToast } from '../../components/ui/Toast'
import type { Question, RubricCriterion } from '../../api/types'
import type { EvaluationMode } from '../../lib/constants'

export const QuestionEditor: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const examId = Number(id)
  const queryClient = useQueryClient()
  const { toast, errorToast } = useToast()

  const [selectedQuestion, setSelectedQuestion] = useState<Question | null>(null)
  const [isNewQuestionModalOpen, setIsNewQuestionModalOpen] = useState(false)

  // Question Form State
  const [newQNumber, setNewQNumber] = useState('')
  const [newQText, setNewQText] = useState('')
  const [newQMaxMarks, setNewQMaxMarks] = useState('10')
  const [newQMode, setNewQMode] = useState<EvaluationMode>('standard')

  // Rubric Editing State
  const [criteria, setCriteria] = useState<RubricCriterion[]>([])
  const [guidance, setGuidance] = useState('')

  const { data: questions = [], isLoading } = useQuery({
    queryKey: ['questions', examId],
    queryFn: () => apiClient.getQuestions(examId),
  })

  const handleSelectQuestion = (q: Question) => {
    setSelectedQuestion(q)
    setCriteria(q.rubric?.criteria ? [...q.rubric.criteria] : [])
    setGuidance(q.rubric?.guidance || '')
  }

  // Select first question by default
  React.useEffect(() => {
    if (questions.length > 0 && !selectedQuestion) {
      handleSelectQuestion(questions[0])
    }
  }, [questions, selectedQuestion])


  const createQuestionMutation = useMutation({
    mutationFn: () =>
      apiClient.createQuestion(examId, {
        question_number: newQNumber,
        text: newQText,
        max_marks: parseFloat(newQMaxMarks) || 10,
        evaluation_mode: newQMode,
      }),
    onSuccess: (newQ: Question) => {
      queryClient.invalidateQueries({ queryKey: ['questions', examId] })
      toast('Question added successfully', 'success')
      setIsNewQuestionModalOpen(false)
      setNewQNumber('')
      setNewQText('')
      handleSelectQuestion(newQ)
    },
    onError: err => errorToast(err),
  })

  const saveRubricMutation = useMutation({
    mutationFn: () => {
      if (!selectedQuestion) throw new Error('No question selected')
      return apiClient.saveRubric(selectedQuestion.id, {
        criteria,
        guidance,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions', examId] })
      toast('Rubric saved successfully', 'success')
    },
    onError: err => errorToast(err),
  })

  const updateModeMutation = useMutation({
    mutationFn: (mode: EvaluationMode) => {
      if (!selectedQuestion) throw new Error('No question selected')
      return apiClient.updateQuestion(selectedQuestion.id, { evaluation_mode: mode })
    },
    onSuccess: (updated: Question) => {
      queryClient.invalidateQueries({ queryKey: ['questions', examId] })
      setSelectedQuestion(updated)
      toast(`Evaluation mode updated to ${updated.evaluation_mode}`, 'success')
    },
    onError: err => errorToast(err),
  })

  const deleteQuestionMutation = useMutation({
    mutationFn: (qId: number) => apiClient.deleteQuestion(qId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions', examId] })
      toast('Question deleted', 'success')
      setSelectedQuestion(null)
    },
    onError: err => errorToast(err),
  })

  // Add / Edit / Remove Criteria
  const addCriterion = () => {
    const nextId = `c${criteria.length + 1}`
    setCriteria([...criteria, { id: nextId, name: `Criterion ${criteria.length + 1}`, max_marks: 2, description: '' }])
  }

  const updateCriterion = (index: number, field: keyof RubricCriterion, value: any) => {
    const updated = [...criteria]
    updated[index] = { ...updated[index], [field]: value }
    setCriteria(updated)
  }

  const removeCriterion = (index: number) => {
    setCriteria(criteria.filter((_, i) => i !== index))
  }

  // Live sum validation
  const currentSum = criteria.reduce((sum, c) => sum + (Number(c.max_marks) || 0), 0)
  const isSumValid = selectedQuestion ? Math.abs(currentSum - selectedQuestion.max_marks) < 0.001 : false

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Link to={`/admin/exams/${examId}`} className="text-xs text-indigo-600 hover:underline">
              ← Back to Exam
            </Link>
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-1">Questions & Rubric Scheme</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Define questions, rubric criteria with live sum check, and toggle Standard vs Reference-grounded mode
          </p>
        </div>

        <Button variant="primary" size="sm" onClick={() => setIsNewQuestionModalOpen(true)}>
          + Add Question
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Questions List */}
        <div className="lg:col-span-1 space-y-3">
          <Card title={`Questions (${questions.length})`}>
            {isLoading ? (
              <div className="p-4 text-center text-slate-400 text-xs">Loading questions...</div>
            ) : questions.length === 0 ? (
              <div className="p-4 text-center text-slate-400 text-xs">No questions configured.</div>
            ) : (
              <div className="space-y-2">
                {questions.map(q => {
                  const isSelected = selectedQuestion?.id === q.id
                  const rubricCriteriaCount = q.rubric?.criteria?.length || 0
                  const sum = q.rubric?.criteria?.reduce((s, c) => s + c.max_marks, 0) || 0
                  const sumMatches = Math.abs(sum - q.max_marks) < 0.001

                  return (
                    <div
                      key={q.id}
                      onClick={() => handleSelectQuestion(q)}
                      className={`p-3 rounded-xl border text-left cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-indigo-50/70 border-indigo-300 ring-2 ring-indigo-200 shadow-xs'
                          : 'bg-white border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-slate-900 text-sm">
                          Q{q.question_number} ({q.max_marks} marks)
                        </span>
                        <Badge variant={q.evaluation_mode === 'reference_grounded' ? 'purple' : 'default'}>
                          {q.evaluation_mode === 'reference_grounded' ? 'Ref-Grounded' : 'Standard'}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-600 line-clamp-2 mb-2">{q.text}</p>
                      <div className="flex items-center justify-between text-[11px]">
                        <span className={sumMatches ? 'text-emerald-600 font-semibold' : 'text-amber-600 font-semibold'}>
                          {rubricCriteriaCount} criteria {sumMatches ? '✓' : `(sum ${sum} ≠ ${q.max_marks})`}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </Card>
        </div>

        {/* Right Column: Selected Question & Rubric Editor */}
        <div className="lg:col-span-2 space-y-6">
          {selectedQuestion ? (
            <>
              {/* Question Overview & Mode Toggle */}
              <Card
                title={`Question ${selectedQuestion.question_number} Details`}
                action={
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => deleteQuestionMutation.mutate(selectedQuestion.id)}
                    isLoading={deleteQuestionMutation.isPending}
                  >
                    Delete Question
                  </Button>
                }
              >
                <div className="space-y-4">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-sm font-medium text-slate-800">
                    {selectedQuestion.text}
                  </div>

                  {/* Mode Toggle (Standard vs Reference Grounded) */}
                  <div className="p-3.5 bg-indigo-50/40 rounded-xl border border-indigo-100 flex items-center justify-between flex-wrap gap-2">
                    <div>
                      <span className="text-xs font-bold text-indigo-950 block">
                        Evaluation Mode
                      </span>
                      <span className="text-xs text-indigo-700/80">
                        {selectedQuestion.evaluation_mode === 'reference_grounded'
                          ? 'Retrieves vector chunks from Pinecone reference documents before LLM evaluation.'
                          : 'Evaluates answer directly against Question text and Rubric (no vector DB required).'}
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        size="sm"
                        variant={selectedQuestion.evaluation_mode === 'standard' ? 'primary' : 'outline'}
                        onClick={() => updateModeMutation.mutate('standard')}
                      >
                        Standard
                      </Button>
                      <Button
                        size="sm"
                        variant={selectedQuestion.evaluation_mode === 'reference_grounded' ? 'primary' : 'outline'}
                        onClick={() => updateModeMutation.mutate('reference_grounded')}
                      >
                        Reference-Grounded
                      </Button>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Rubric Criteria Editor with Live Sum Check */}
              <Card
                title="Structured Rubric Scheme"
                subtitle="The LLM marks against these explicit criteria. Sum must equal question max marks."
                action={
                  <Button size="sm" variant="outline" onClick={addCriterion}>
                    + Add Criterion
                  </Button>
                }
              >
                <div className="space-y-3">
                  {criteria.map((c, idx) => (
                    <div
                      key={c.id || idx}
                      className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 space-y-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="w-16">
                          <span className="text-[10px] font-bold text-slate-400 uppercase">ID</span>
                          <input
                            type="text"
                            value={c.id}
                            onChange={e => updateCriterion(idx, 'id', e.target.value)}
                            className="w-full px-2 py-1 text-xs font-mono font-bold border border-slate-300 rounded bg-white"
                          />
                        </div>
                        <div className="flex-1">
                          <span className="text-[10px] font-bold text-slate-400 uppercase">Criterion Name</span>
                          <input
                            type="text"
                            value={c.name}
                            onChange={e => updateCriterion(idx, 'name', e.target.value)}
                            className="w-full px-2 py-1 text-xs border border-slate-300 rounded bg-white"
                            placeholder="e.g. Correct diagram"
                          />
                        </div>
                        <div className="w-24">
                          <span className="text-[10px] font-bold text-slate-400 uppercase">Max Marks</span>
                          <input
                            type="number"
                            step="0.5"
                            min="0"
                            value={c.max_marks}
                            onChange={e => updateCriterion(idx, 'max_marks', parseFloat(e.target.value) || 0)}
                            className="w-full px-2 py-1 text-xs font-bold text-right border border-slate-300 rounded bg-white"
                          />
                        </div>
                        <div className="pt-3">
                          <button
                            type="button"
                            onClick={() => removeCriterion(idx)}
                            className="text-slate-400 hover:text-rose-600 p-1"
                            title="Remove criterion"
                          >
                            ✕
                          </button>
                        </div>
                      </div>
                      <div>
                        <input
                          type="text"
                          value={c.description || ''}
                          onChange={e => updateCriterion(idx, 'description', e.target.value)}
                          placeholder="Description or requirements for full marks..."
                          className="w-full px-2 py-1 text-xs text-slate-600 border border-slate-200 rounded bg-white"
                        />
                      </div>
                    </div>
                  ))}

                  {criteria.length === 0 && (
                    <div className="p-6 text-center text-slate-400 text-xs border border-dashed rounded-lg">
                      No criteria added yet. Click "+ Add Criterion" to start.
                    </div>
                  )}

                  {/* Live Sum Check Bar */}
                  <div
                    className={`p-3 rounded-lg border text-xs flex items-center justify-between ${
                      isSumValid
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                        : 'bg-rose-50 border-rose-200 text-rose-800'
                    }`}
                  >
                    <span className="font-semibold">
                      Criteria Sum: {currentSum} / {selectedQuestion.max_marks} max marks
                    </span>
                    <span>
                      {isSumValid ? '✓ Sum matches max marks exactly' : `⚠ Sum mismatch: difference of ${Math.abs(currentSum - selectedQuestion.max_marks)} marks`}
                    </span>
                  </div>

                  {/* Guidance */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                      Examiner / LLM Guidance (Optional)
                    </label>
                    <textarea
                      rows={2}
                      value={guidance}
                      onChange={e => setGuidance(e.target.value)}
                      placeholder="e.g. Accept alternative terminology for handshake steps..."
                      className="w-full p-2 text-xs border border-slate-300 rounded-lg bg-white"
                    />
                  </div>

                  <div className="flex justify-end pt-3 border-t border-slate-100">
                    <Button
                      variant="primary"
                      disabled={!isSumValid}
                      isLoading={saveRubricMutation.isPending}
                      onClick={() => saveRubricMutation.mutate()}
                    >
                      Save Rubric Scheme
                    </Button>
                  </div>
                </div>
              </Card>
            </>
          ) : (
            <Card>
              <div className="p-12 text-center text-slate-400 text-sm">
                Select a question from the left or create a new one.
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* Add Question Modal */}
      <Modal
        isOpen={isNewQuestionModalOpen}
        onClose={() => setIsNewQuestionModalOpen(false)}
        title="Add Exam Question"
      >
        <form
          onSubmit={e => {
            e.preventDefault()
            createQuestionMutation.mutate()
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Question Number"
              required
              value={newQNumber}
              onChange={e => setNewQNumber(e.target.value)}
              placeholder="e.g. 1 or 2a"
            />
            <Input
              label="Max Marks"
              type="number"
              step="0.5"
              min="1"
              required
              value={newQMaxMarks}
              onChange={e => setNewQMaxMarks(e.target.value)}
            />
          </div>

          <Textarea
            label="Question Text"
            required
            rows={3}
            value={newQText}
            onChange={e => setNewQText(e.target.value)}
            placeholder="Type the exact question text here..."
          />

          <Select
            label="Evaluation Mode"
            value={newQMode}
            onChange={e => setNewQMode(e.target.value as EvaluationMode)}
            options={[
              { value: 'standard', label: 'Standard (Prompt from Question + Answer + Rubric)' },
              { value: 'reference_grounded', label: 'Reference-grounded (Includes Pinecone reference chunks)' },
            ]}
          />

          <div className="flex justify-end space-x-2 pt-3 border-t border-slate-100">
            <Button variant="secondary" type="button" onClick={() => setIsNewQuestionModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" isLoading={createQuestionMutation.isPending}>
              Add Question
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
