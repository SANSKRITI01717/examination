import React from 'react'

export const Table: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <div className="w-full overflow-x-auto">
    <table className={`w-full text-left text-sm text-slate-700 ${className}`}>{children}</table>
  </div>
)

export const TableHeader: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <thead className={`bg-slate-50 text-xs uppercase font-semibold text-slate-500 border-b border-slate-200 ${className}`}>
    {children}
  </thead>
)

export const TableBody: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <tbody className={`divide-y divide-slate-200 ${className}`}>{children}</tbody>
)

export const TableRow: React.FC<{ children: React.ReactNode; className?: string; onClick?: () => void }> = ({
  children,
  className = '',
  onClick,
}) => (
  <tr
    onClick={onClick}
    className={`${onClick ? 'cursor-pointer hover:bg-slate-50/80 transition-colors' : ''} ${className}`}
  >
    {children}
  </tr>
)

export const TableHead: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <th className={`px-4 py-3 ${className}`}>{children}</th>
)

export const TableCell: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <td className={`px-4 py-3.5 whitespace-nowrap ${className}`}>{children}</td>
)
