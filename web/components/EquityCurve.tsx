'use client'

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

// Mock data - will be replaced with real data from Supabase
const mockData = [
  { time: '09:30', equity: 1000 },
  { time: '10:00', equity: 1012 },
  { time: '10:30', equity: 1008 },
  { time: '11:00', equity: 1025 },
  { time: '11:30', equity: 1018 },
  { time: '12:00', equity: 1018 },
  { time: '12:30', equity: 1018 },
  { time: '13:00', equity: 1032 },
  { time: '13:30', equity: 1045 },
  { time: '14:00', equity: 1038 },
  { time: '14:30', equity: 1052 },
  { time: '15:00', equity: 1065 },
]

export function EquityCurve() {
  const startingEquity = mockData[0]?.equity || 1000
  const currentEquity = mockData[mockData.length - 1]?.equity || 1000
  const pnl = currentEquity - startingEquity
  const pnlPct = ((pnl / startingEquity) * 100).toFixed(2)

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <div>
          <span className="text-3xl font-bold">${currentEquity.toFixed(2)}</span>
          <span className={`ml-2 text-sm ${pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)} ({pnlPct}%)
          </span>
        </div>
        <div className="flex gap-2 text-xs">
          <button className="px-2 py-1 bg-slate-700 rounded">1D</button>
          <button className="px-2 py-1 bg-slate-600 rounded">1W</button>
          <button className="px-2 py-1 bg-slate-600 rounded">1M</button>
          <button className="px-2 py-1 bg-slate-600 rounded">ALL</button>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={mockData}>
          <XAxis
            dataKey="time"
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
          />
          <YAxis
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
            domain={['dataMin - 10', 'dataMax + 10']}
            tickFormatter={(v) => `$${v}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#94a3b8' }}
          />
          <ReferenceLine y={startingEquity} stroke="#475569" strokeDasharray="3 3" />
          <Line
            type="monotone"
            dataKey="equity"
            stroke={pnl >= 0 ? '#10b981' : '#ef4444'}
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
