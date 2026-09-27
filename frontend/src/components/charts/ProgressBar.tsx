import React from 'react'

interface ProgressBarProps {
  label: string
  current: number
  total: number
  color?: 'indigo' | 'emerald' | 'amber' | 'purple'
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  label,
  current,
  total,
  color = 'indigo',
}) => {
  const percentage = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0

  const colorStyles = {
    indigo: 'bg-indigo-600',
    emerald: 'bg-emerald-600',
    amber: 'bg-amber-500',
    purple: 'bg-purple-600',
  }

  return (
    <div className="w-full">
      <div className="flex justify-between items-center text-xs font-semibold mb-1.5">
        <span className="text-slate-700">{label}</span>
        <span className="text-slate-500">
          {current} / {total} ({percentage}%)
        </span>
      </div>
      <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden border border-slate-200/60">
        <div
          className={`h-full ${colorStyles[color]} transition-all duration-500 rounded-full`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
