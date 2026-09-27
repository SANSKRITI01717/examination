import React, { createContext, useContext, useState, useCallback } from 'react'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

interface ToastMessage {
  id: number
  message: string
  type: ToastType
}

interface ToastContextType {
  toast: (message: string, type?: ToastType) => void
  errorToast: (err: any) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const removeToast = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const toast = useCallback((message: string, type: ToastType = 'info') => {
    const id = Date.now() + Math.random()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => {
      removeToast(id)
    }, 4000)
  }, [removeToast])

  const errorToast = useCallback((err: any) => {
    let msg = 'An unexpected error occurred'
    if (typeof err === 'string') {
      msg = err
    } else if (err?.error?.message) {
      msg = err.error.message
    } else if (err?.message) {
      msg = err.message
    }
    toast(msg, 'error')
  }, [toast])

  return (
    <ToastContext.Provider value={{ toast, errorToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col space-y-2 max-w-sm pointer-events-none">
        {toasts.map(t => {
          const typeStyles = {
            success: 'bg-emerald-600 text-white border-emerald-700',
            error: 'bg-rose-600 text-white border-rose-700',
            warning: 'bg-amber-600 text-white border-amber-700',
            info: 'bg-slate-900 text-white border-slate-800',
          }
          return (
            <div
              key={t.id}
              className={`pointer-events-auto px-4 py-3 rounded-xl shadow-lg border text-sm font-medium flex items-center justify-between transition-all duration-300 transform translate-y-0 ${typeStyles[t.type]}`}
            >
              <span>{t.message}</span>
              <button
                onClick={() => removeToast(t.id)}
                className="ml-3 text-white/80 hover:text-white"
              >
                ✕
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextType {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}
