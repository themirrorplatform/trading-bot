'use client'

interface SignalGaugeProps {
  label: string
  value: number
  min: number
  max: number
}

export function SignalGauge({ label, value, min, max }: SignalGaugeProps) {
  const range = max - min
  const normalized = ((value - min) / range) * 100
  const clamped = Math.max(0, Math.min(100, normalized))

  // Color based on position
  let color = 'bg-slate-400'
  if (label.includes('DVS') || label.includes('EQS')) {
    color = value >= 0.8 ? 'bg-emerald-400' : value >= 0.6 ? 'bg-yellow-400' : 'bg-red-400'
  } else if (label.includes('VWAP') || label.includes('Vol')) {
    const abs = Math.abs(value)
    color = abs < 1 ? 'bg-slate-400' : abs < 2 ? 'bg-yellow-400' : 'bg-orange-400'
  }

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-slate-400">{label}</span>
        <span className="font-mono">{value.toFixed(2)}</span>
      </div>
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} transition-all duration-300`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-slate-500 mt-1">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  )
}
