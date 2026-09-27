import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { ToastProvider } from './components/ui/Toast'
import { AppShell } from './components/layout/AppShell'

// Pages
import { Login } from './pages/Login'
import { AdminDashboard } from './pages/admin/AdminDashboard'
import { UsersAdmin } from './pages/admin/UsersAdmin'
import { ExamDetail } from './pages/admin/ExamDetail'
import { QuestionEditor } from './pages/admin/QuestionEditor'
import { ReferenceDocs } from './pages/admin/ReferenceDocs'
import { SheetUpload } from './pages/admin/SheetUpload'
import { PageMapping } from './pages/admin/PageMapping'
import { Assignments } from './pages/admin/Assignments'
import { Processing } from './pages/admin/Processing'

import { ExaminerDashboard } from './pages/examiner/ExaminerDashboard'
import { AnswerList } from './pages/examiner/AnswerList'
import { Workspace } from './pages/examiner/Workspace'

import { ModeratorDashboard } from './pages/moderator/ModeratorDashboard'
import { ModerationView } from './pages/moderator/ModerationView'

import { Analytics } from './pages/shared/Analytics'
import { Results } from './pages/shared/Results'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 10,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

// Root redirector based on authenticated user's role
const RootRedirect: React.FC = () => {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-indigo-600 border-r-transparent"></div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (user.role === 'admin') return <Navigate to="/admin" replace />
  if (user.role === 'examiner') return <Navigate to="/examiner" replace />
  if (user.role === 'moderator') return <Navigate to="/moderator" replace />

  return <Navigate to="/login" replace />
}

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>
          <BrowserRouter>
            <Routes>
              {/* Public Routes */}
              <Route path="/login" element={<Login />} />

              {/* Admin Routes */}
              <Route
                path="/admin"
                element={
                  <ProtectedRoute roles={['admin']}>
                    <AppShell title="Admin Portal" subtitle="System & Exam Management" />
                  </ProtectedRoute>
                }
              >
                <Route index element={<AdminDashboard />} />
                <Route path="users" element={<UsersAdmin />} />
                <Route path="exams/new" element={<ExamDetail />} />
                <Route path="exams/:id" element={<ExamDetail />} />
                <Route path="exams/:id/questions" element={<QuestionEditor />} />
                <Route path="exams/:id/references" element={<ReferenceDocs />} />
                <Route path="exams/:id/sheets" element={<SheetUpload />} />
                <Route path="sheets/:id/mapping" element={<PageMapping />} />
                <Route path="exams/:id/assignments" element={<Assignments />} />
                <Route path="exams/:id/processing" element={<Processing />} />
              </Route>

              {/* Examiner Routes */}
              <Route
                path="/examiner"
                element={
                  <ProtectedRoute roles={['examiner']}>
                    <AppShell title="Examiner Portal" subtitle="Evaluation & Marking" />
                  </ProtectedRoute>
                }
              >
                <Route index element={<ExaminerDashboard />} />
                <Route path="exams/:id/answers" element={<AnswerList />} />
                <Route path="answers/:id" element={<Workspace />} />
              </Route>

              {/* Moderator Routes */}
              <Route
                path="/moderator"
                element={
                  <ProtectedRoute roles={['moderator']}>
                    <AppShell title="Moderator Portal" subtitle="Anomaly Review & Resolution" />
                  </ProtectedRoute>
                }
              >
                <Route index element={<ModeratorDashboard />} />
                <Route path="answers/:id" element={<ModerationView />} />
              </Route>

              {/* Shared Admin/Moderator Analytics & Results */}
              <Route
                path="/exams/:id"
                element={
                  <ProtectedRoute roles={['admin', 'moderator']}>
                    <AppShell title="Examination Performance" />
                  </ProtectedRoute>
                }
              >
                <Route path="analytics" element={<Analytics />} />
                <Route path="results" element={<Results />} />
              </Route>

              {/* Root & Catch-all */}
              <Route path="/" element={<RootRedirect />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
