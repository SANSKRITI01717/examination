import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/ui/Input'
import { Modal } from '../../components/ui/Modal'
import { Badge } from '../../components/ui/Badge'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/ui/Table'
import { useToast } from '../../components/ui/Toast'
import type { UserRole } from '../../lib/constants'


export const UsersAdmin: React.FC = () => {
  const queryClient = useQueryClient()
  const { toast, errorToast } = useToast()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [role, setRole] = useState<UserRole>('examiner')

  const { data, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => apiClient.getUsers(),
  })

  const createMutation = useMutation({
    mutationFn: (userData: { email: string; full_name: string; role: UserRole }) =>
      apiClient.createUser(userData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast('User account created', 'success')
      setIsCreateOpen(false)
      setEmail('')
      setFullName('')
    },
    onError: err => errorToast(err),
  })

  const toggleStatusMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      apiClient.updateUser(id, { is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast('User status updated', 'success')
    },
    onError: err => errorToast(err),
  })

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({ email, full_name: fullName, role })
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">User & Examiner Accounts</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage university users with role-based access control (Admin, Examiner, Moderator)
          </p>
        </div>
        <Button variant="primary" size="sm" onClick={() => setIsCreateOpen(true)}>
          + Create User
        </Button>
      </div>

      <Card title="System Accounts">
        {isLoading ? (
          <div className="p-8 text-center text-slate-500 text-sm">Loading users...</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Full Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items.map(u => (
                <TableRow key={u.id}>
                  <TableCell className="font-semibold text-slate-900">{u.full_name}</TableCell>
                  <TableCell className="text-slate-600 font-mono text-xs">{u.email}</TableCell>
                  <TableCell>
                    <Badge variant={u.role === 'admin' ? 'purple' : u.role === 'examiner' ? 'info' : 'warning'}>
                      {u.role}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                        u.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant={u.is_active ? 'outline' : 'secondary'}
                      onClick={() => toggleStatusMutation.mutate({ id: u.id, is_active: !u.is_active })}
                      isLoading={toggleStatusMutation.isPending}
                    >
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* Create Modal */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Create User Account">
        <form onSubmit={handleCreate} className="space-y-4">
          <Input
            label="Full Name"
            required
            value={fullName}
            onChange={e => setFullName(e.target.value)}
            placeholder="e.g. Dr. Jane Smith"
          />
          <Input
            label="Email Address"
            type="email"
            required
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="e.g. jsmith@univ.edu"
          />
          <Select
            label="Role"
            value={role}
            onChange={e => setRole(e.target.value as UserRole)}
            options={[
              { value: 'examiner', label: 'Examiner (Marks assigned scripts)' },
              { value: 'moderator', label: 'Moderator (Resolves anomalies & overrides)' },
              { value: 'admin', label: 'Admin (Manages exams, rubrics, uploads)' },
            ]}
          />
          <div className="flex justify-end space-x-2 pt-3 border-t border-slate-100">
            <Button variant="secondary" type="button" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" isLoading={createMutation.isPending}>
              Create Account
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
