'use client'

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'

interface EquityPoint {
  time: string
  equity: number
  pnl: number
}

export function EquityCurve() {
  const [data, setData] = useState<EquityPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [timeframe, setTimeframe] = useState<'1D' | '1W' | '1M' | 'ALL'>('1D')
  const [startingEquity, setStartingEquity] = useState(1000)

  useEffect(() => {
    async function fetchEquityData() {
      setLoading(true)
      const supabase = createClient()

      // Calculate date range based on timeframe
      const now = new Date()
      let startDate: Date
      switch (timeframe) {
        case '1D':
          startDate = new Date(now.toISOString().split('T')[0])
          break
        case '1W':
          startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
          break
        case '1M':
          startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
          break
        case 'ALL':
        default:
          startDate = new Date('2024-01-01')
      }

      // Fetch fill events (trades) within timeframe
      const { data: fills } = await supabase
        .from('events')
        .select('*')
        .eq('event_type', 'FILL_EVENT')
        .gte('timestamp', startDate.toISOString())
        .order('timestamp', { ascending: true })

      if (!fills || fills.length === 0) {
        // Show placeholder data
        setData([
          { time: 'Start', equity: startingEquity, pnl: 0 },
          { time: 'Now', equity: startingEquity, pnl: 0 },
        ])
        setLoading(false)
        return
      }

      // Build cumulative equity curve
      let cumPnl = 0
      const equityPoints: EquityPoint[] = [
        { time: 'Start', equity: startingEquity, pnl: 0 }
      ]

      fills.forEach((fill: any) => {
        const pnl = fill.payload?.pnl_usd || 0
        cumPnl += pnl
        const timestamp = new Date(fill.timestamp)
        const timeStr = timeframe === '1D'
          ? timestamp.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
          : timestamp.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

        equityPoints.push({
          time: timeStr,
          equity: startingEquity + cumPnl,
          pnl: pnl
        })
      })

      setData(equityPoints)
      setLoading(false)
    }

    fetchEquityData()

    // Set up real-time subscription
    const supabase = createClient()
    const channel = supabase
      .channel('equity-updates')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'events', filter: 'event_type=eq.FILL_EVENT' },
        () => {
          fetchEquityData()
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [timeframe, startingEquity])

  const currentEquity = data.length > 0 ? data[data.length - 1].equity : startingEquity
  const pnl = currentEquity - startingEquity
  const pnlPct = startingEquity > 0 ? ((pnl / startingEquity) * 100).toFixed(2) : '0.00'

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
          {(['1D', '1W', '1M', 'ALL'] as const).map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-2 py-1 rounded ${timeframe === tf ? 'bg-slate-700' : 'bg-slate-600 hover:bg-slate-500'}`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>
      {loading ? (
        <div className="h-[250px] flex items-center justify-center text-slate-500">
          Loading equity data...
        </div>
      ) : data.length <= 2 ? (
        <div className="h-[250px] flex items-center justify-center text-slate-500">
          No trades in selected period. Complete trades to build equity curve.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={data}>
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
              formatter={(value: number, name: string) => [
                `$${value.toFixed(2)}`,
                name === 'equity' ? 'Equity' : 'Trade P&L'
              ]}
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
      )}
    </div>
  )
}
