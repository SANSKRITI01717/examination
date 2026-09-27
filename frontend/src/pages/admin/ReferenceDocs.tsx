import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/ui/Input'
import { Badge } from '../../components/ui/Badge'
import { useToast } from '../../components/ui/Toast'
import type { DocType } from '../../lib/constants'

export const ReferenceDocs: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const examId = Number(id)
  const queryClient = useQueryClient()
  const { toast, errorToast } = useToast()

  const [docTitle, setDocTitle] = useState('')
  const [docType, setDocType] = useState<DocType>('guideline')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[] | null>(null)
  const [isSearching, setIsSearching] = useState(false)

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['referenceDocs', examId],
    queryFn: () => apiClient.getDocuments(examId),
  })

  const uploadMutation = useMutation({
    mutationFn: () => apiClient.uploadDocument(examId, docTitle, docType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['referenceDocs', examId] })
      toast('Reference document indexed to Pinecone', 'success')
      setDocTitle('')
    },
    onError: err => errorToast(err),
  })

  const deleteMutation = useMutation({
    mutationFn: (docId: number) => apiClient.deleteDocument(docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['referenceDocs', examId] })
      toast('Reference document deleted', 'success')
    },
    onError: err => errorToast(err),
  })

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    setIsSearching(true)
    try {
      const res = await apiClient.searchReference(examId, searchQuery)
      setSearchResults(res.chunks)
      toast('Retrieved vector chunks', 'success')
    } catch (err) {
      errorToast(err)
    } finally {
      setIsSearching(false)
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
        <h2 className="text-xl font-bold text-slate-900 mt-1">Reference Documents & Vector Indexing</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Official answers, guidelines, and course notes chunked and embedded in Pinecone for reference-grounded questions
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Reference Document Form */}
        <div className="lg:col-span-1 space-y-4">
          <Card title="Upload Reference Material">
            <form
              onSubmit={e => {
                e.preventDefault()
                uploadMutation.mutate()
              }}
              className="space-y-4"
            >
              <Input
                label="Document Title"
                required
                value={docTitle}
                onChange={e => setDocTitle(e.target.value)}
                placeholder="e.g. Raft Consensus Notes.pdf"
              />

              <Select
                label="Document Type"
                value={docType}
                onChange={e => setDocType(e.target.value as DocType)}
                options={[
                  { value: 'guideline', label: 'Evaluation Guideline' },
                  { value: 'official_answer', label: 'Official Model Answer' },
                  { value: 'syllabus', label: 'Course Syllabus' },
                  { value: 'other', label: 'Other Faculty Material' },
                ]}
              />

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600">
                <span className="font-semibold block mb-1">Vector Storage Rules:</span>
                Student answers are never stored in vector DBs. Only official reference documents are chunked and embedded.
              </div>

              <Button
                variant="primary"
                className="w-full"
                type="submit"
                disabled={!docTitle.trim()}
                isLoading={uploadMutation.isPending}
              >
                Upload & Chunk Index
              </Button>
            </form>
          </Card>
        </div>

        {/* Reference Document List */}
        <div className="lg:col-span-2 space-y-6">
          <Card title={`Indexed Reference Documents (${documents.length})`}>
            {isLoading ? (
              <div className="p-6 text-center text-slate-400 text-xs">Loading documents...</div>
            ) : documents.length === 0 ? (
              <div className="p-6 text-center text-slate-400 text-xs">
                No reference documents uploaded for this exam.
              </div>
            ) : (
              <div className="space-y-3">
                {documents.map(doc => (
                  <div
                    key={doc.id}
                    className="p-3.5 rounded-xl border border-slate-200 bg-white flex items-center justify-between shadow-xs"
                  >
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-semibold text-slate-900">{doc.title}</span>
                        <Badge
                          variant={
                            doc.status === 'indexed'
                              ? 'success'
                              : doc.status === 'indexing'
                              ? 'info'
                              : 'warning'
                          }
                        >
                          {doc.status}
                        </Badge>
                      </div>
                      <div className="text-xs text-slate-500 mt-1 flex items-center space-x-3">
                        <span>Type: {doc.doc_type}</span>
                        <span>•</span>
                        <span>{doc.chunk_count} vector chunks</span>
                        <span>•</span>
                        <span>Pinecone Index: ready</span>
                      </div>
                    </div>

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => deleteMutation.mutate(doc.id)}
                      isLoading={deleteMutation.isPending}
                      className="text-rose-600 hover:bg-rose-50"
                    >
                      Delete
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* D5: Retrieval Test Box */}
          <Card
            title="Pinecone Retrieval Test Box"
            subtitle="Test similarity search against the indexed reference material (D5)"
          >
            <form onSubmit={handleSearch} className="flex gap-2 mb-4">
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Enter search query (e.g. Raft election timeout rules)..."
                className="flex-1 px-3.5 py-2 rounded-lg border border-slate-300 text-xs bg-white text-slate-900"
              />
              <Button size="sm" variant="primary" type="submit" isLoading={isSearching}>
                Test Search
              </Button>
            </form>

            {searchResults && (
              <div className="space-y-2.5">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Top Retrieved Chunks ({searchResults.length})
                </span>
                {searchResults.map((c, i) => (
                  <div key={i} className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                    <div className="flex justify-between items-center font-semibold text-slate-800 mb-1">
                      <span>{c.title} (Chunk #{c.chunk_index})</span>
                      <span className="text-indigo-600 font-mono">Score: {c.score}</span>
                    </div>
                    <p className="text-slate-600 leading-relaxed font-mono">{c.text}</p>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
