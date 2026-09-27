import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import type { UserRole } from '../lib/constants'

interface ProtectedRouteProps {
  children: React.ReactNode
  roles?: UserRole[]
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, roles }) => {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-indigo-600 border-r-transparent"></div>
          <p className="mt-2 text-sm text-slate-600 font-medium">Authenticating session...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (roles && !roles.includes(user.role)) {
    // Redirect unauthorized user to their primary landing dashboard
    const roleDashboardMap: Record<string, string> = {
      admin: '/admin',
      examiner: '/examiner',
      moderator: '/moderator',
    }
    return <Navigate to={roleDashboardMap[user.role] || '/login'} replace />
  }

  return <>{children}</>
}
