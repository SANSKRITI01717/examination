import React, { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { PageHeader } from './PageHeader'

interface AppShellProps {
  title?: string
  subtitle?: string
  action?: React.ReactNode
  children?: React.ReactNode
}

export const AppShell: React.FC<AppShellProps> = ({ title = 'OSM Platform', subtitle, action, children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 overflow-hidden font-sans">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <PageHeader
          title={title}
          subtitle={subtitle}
          action={action}
          onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
        />

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto w-full">
            {children || <Outlet />}
          </div>
        </main>
      </div>
    </div>
  )
}
