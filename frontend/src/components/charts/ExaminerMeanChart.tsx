import React from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts'
import type { ExaminerAnalytics } from '../../api/types'

interface ExaminerMeanChartProps {
  data: ExaminerAnalytics[]
}

export const ExaminerMeanChart: React.FC<ExaminerMeanChartProps> = ({ data }) => {
  const chartData = data.map(item => ({
    name: item.examiner.full_name.replace('Dr. ', '').replace('Prof. ', ''),
    Mean: item.mean,
    Global: item.mean - item.mean_vs_global,
    SD: item.sd,
  }))

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
          <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} />
          <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', border: 'none', color: '#fff', fontSize: '12px' }}
          />
          <Legend wrapperStyle={{ fontSize: '12px' }} />
          <Bar dataKey="Mean" fill="#6366f1" radius={[4, 4, 0, 0]} name="Examiner Mean" />
          <Bar dataKey="Global" fill="#94a3b8" radius={[4, 4, 0, 0]} name="Global Benchmark" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
