import React from 'react'
import { useAuth } from '../../auth/AuthContext'
import { apiClient } from '../../api/client'

interface PageHeaderProps {
  title: string
  subtitle?: string
  action?: React.ReactNode
  onMenuToggle: () => void
}

export const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle, action, onMenuToggle }) => {
  const { user, logout, switchRole } = useAuth()

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center space-x-3">
        {/* Hamburger for mobile */}
        <button
          onClick={onMenuToggle}
          className="p-2 -ml-2 rounded-lg text-slate-600 hover:bg-slate-100 lg:hidden"
          aria-label="Open navigation menu"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <div>
          <h1 className="text-lg font-bold text-slate-900 tracking-tight leading-none">{title}</h1>
          {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {action && <div className="hidden sm:block">{action}</div>}

        {/* Demo Fast Role Switcher (Visible in Mock Mode for easy hackathon demo) */}
        {apiClient.isMockMode && user && (
          <div className="hidden md:flex items-center space-x-1 p-1 bg-slate-100 rounded-lg text-xs font-semibold">
            <span className="text-slate-400 px-1 text-[10px] uppercase">Switch:</span>
            <button
              onClick={() => switchRole('admin')}
              className={`px-2 py-1 rounded cursor-pointer ${
                user.role === 'admin' ? 'bg-indigo-600 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-200'
              }`}
            >
              Admin
            </button>
            <button
              onClick={() => switchRole('examiner')}
              className={`px-2 py-1 rounded cursor-pointer ${
                user.role === 'examiner' ? 'bg-indigo-600 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-200'
              }`}
            >
              Examiner
            </button>
            <button
              onClick={() => switchRole('moderator')}
              className={`px-2 py-1 rounded cursor-pointer ${
                user.role === 'moderator' ? 'bg-indigo-600 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-200'
              }`}
            >
              Moderator
            </button>
          </div>
        )}

        {/* User profile & Logout */}
        {user && (
          <div className="flex items-center space-x-3 pl-2 border-l border-slate-200">
            <div className="hidden sm:block text-right">
              <div className="text-xs font-semibold text-slate-800">{user.full_name}</div>
              <div className="text-[10px] text-slate-500 capitalize">{user.role}</div>
            </div>
            <button
              onClick={logout}
              title="Logout"
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                />
              </svg>
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
