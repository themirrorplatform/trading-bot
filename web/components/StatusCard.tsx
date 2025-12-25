'use client'

interface StatusCardProps {
  title: string
  value: string
  status: 'success' | 'error' | 'warning' | 'neutral'
}

const statusColors = {
  success: 'text-emerald-400',
  error: 'text-red-400',
  warning: 'text-yellow-400',
  neutral: 'text-slate-300',
}

const statusBg = {
  success: 'bg-emerald-500/10 border-emerald-500/20',
  error: 'bg-red-500/10 border-red-500/20',
  warning: 'bg-yellow-500/10 border-yellow-500/20',
  neutral: 'bg-slate-500/10 border-slate-500/20',
}

export function StatusCard({ title, value, status }: StatusCardProps) {
  return (
    <div className={`rounded-lg border p-4 ${statusBg[status]}`}>
      <p className="text-sm text-slate-400">{title}</p>
      <p className={`text-2xl font-bold mt-1 ${statusColors[status]}`}>
        {value}
      </p>
    </div>
  )
}
