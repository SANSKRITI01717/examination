import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/ui/Input'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/ui/Table'
import { Badge } from '../../components/ui/Badge'
import { useToast } from '../../components/ui/Toast'

export const SheetUpload: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const examId = Number(id)
  const queryClient = useQueryClient()
  const { toast, errorToast } = useToast()

  const [selectedStudentId, setSelectedStudentId] = useState<number>(101)
  const [pageCount, setPageCount] = useState<string>('3')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])

  const { data: sheetsData, isLoading: sheetsLoading } = useQuery({
    queryKey: ['sheets', examId],
    queryFn: () => apiClient.getSheets(examId),
  })

  const { data: studentsData } = useQuery({
    queryKey: ['students'],
    queryFn: () => apiClient.getStudents(),
  })

  React.useEffect(() => {
    if (studentsData?.items && studentsData.items.length > 0) {
      if (!studentsData.items.some(s => s.id === selectedStudentId)) {
        setSelectedStudentId(studentsData.items[0].id)
      }
    }
  }, [studentsData, selectedStudentId])

  const uploadMutation = useMutation({
    mutationFn: () =>
      apiClient.uploadSheet(
        examId,
        selectedStudentId,
        selectedFiles.length > 0 ? selectedFiles : parseInt(pageCount) || 3
      ),
    onSuccess: (newSheet: any) => {
      queryClient.invalidateQueries({ queryKey: ['sheets', examId] })
      toast(`Answer script uploaded! Generated anonymous code: ${newSheet.anon_code}`, 'success')
      setSelectedFiles([])
    },
    onError: err => errorToast(err),
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Link to={`/admin/exams/${examId}`} className="text-xs text-indigo-600 hover:underline">
              ← Back to Exam
            </Link>
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-1">Answer Sheets & Scans</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Upload student answer scripts (PDF or image pages). Anonymous code is automatically generated for blind marking.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Form */}
        <div className="lg:col-span-1">
          <Card title="Upload Student Script">
            <form
              onSubmit={e => {
                e.preventDefault()
                uploadMutation.mutate()
              }}
              className="space-y-4"
            >
              <Select
                label="Student Candidate"
                value={selectedStudentId}
                onChange={e => setSelectedStudentId(Number(e.target.value))}
                options={studentsData?.items.map(s => ({
                  value: s.id,
                  label: `${s.roll_number} - ${s.full_name} (${s.department || 'CS'})`,
                }))}
              />

              <Input
                label="Page Count in Scan"
                type="number"
                min="1"
                max="50"
                value={pageCount}
                onChange={e => setPageCount(e.target.value)}
              />

              {/* Drag and Drop Zone representation */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Scan Document (PDF / JPEG / PNG)
                </label>
                <label className="border-2 border-dashed border-slate-300 rounded-xl p-6 text-center hover:border-indigo-500 transition-colors bg-slate-50/50 cursor-pointer block">
                  <input
                    type="file"
                    multiple
                    accept=".pdf,image/jpeg,image/png"
                    className="hidden"
                    onChange={e => {
                      if (e.target.files) {
                        const filesArr = Array.from(e.target.files)
                        setSelectedFiles(filesArr)
                        setPageCount(String(filesArr.length))
                      }
                    }}
                  />
                  <svg
                    className="mx-auto h-8 w-8 text-slate-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                  </svg>
                  <p className="mt-2 text-xs text-slate-600 font-medium">
                    {selectedFiles.length > 0
                      ? `${selectedFiles.length} file(s) selected: ${selectedFiles.map(f => f.name).join(', ')}`
                      : 'Click or drop handwritten script scan here'}
                  </p>
                  <p className="text-[11px] text-slate-400">PDF will be split into page images automatically (Max 15MB)</p>
                </label>
              </div>

              <Button
                variant="primary"
                className="w-full"
                type="submit"
                isLoading={uploadMutation.isPending}
              >
                Upload & Register Sheet
              </Button>
            </form>
          </Card>
        </div>

        {/* Uploaded Sheets Table */}
        <div className="lg:col-span-2">
          <Card title={`Uploaded Answer Sheets (${sheetsData?.items.length || 0})`}>
            {sheetsLoading ? (
              <div className="p-8 text-center text-slate-400 text-xs">Loading sheets...</div>
            ) : sheetsData?.items.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">No sheets uploaded yet.</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Anon Code</TableHead>
                    <TableHead>Student (Admin Only)</TableHead>
                    <TableHead>Pages</TableHead>
                    <TableHead>Mapping Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sheetsData?.items.map(s => (
                    <TableRow key={s.id}>
                      <TableCell className="font-mono font-bold text-indigo-600">
                        {s.anon_code}
                      </TableCell>
                      <TableCell className="text-xs">
                        <div className="font-medium text-slate-900">{s.student?.full_name}</div>
                        <div className="text-slate-400 font-mono">{s.student?.roll_number}</div>
                      </TableCell>
                      <TableCell className="text-xs text-slate-600 font-semibold">
                        {s.page_count} pages
                      </TableCell>
                      <TableCell>
                        <Badge variant={s.status === 'mapped' ? 'success' : 'warning'}>
                          {s.status === 'mapped' ? 'Mapped' : 'Unmapped'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Link to={`/admin/sheets/${s.id}/mapping`}>
                          <Button size="sm" variant={s.status === 'mapped' ? 'outline' : 'primary'}>
                            {s.status === 'mapped' ? 'Edit Mapping' : 'Map Pages'}
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
      </div>
    </div>
  )
}
