'use client'

import { format } from 'date-fns'

interface Trade {
  id: string
  timestamp: string
  payload: {
    direction: string
    contracts: number
    fill_price: number
    pnl_usd?: number
  }
}

interface RecentTradesProps {
  trades: Trade[]
}

export function RecentTrades({ trades }: RecentTradesProps) {
  if (trades.length === 0) {
    return (
      <div className="text-center text-slate-500 py-8">
        No trades today
      </div>
    )
  }

  return (
    <div className="space-y-2 max-h-64 overflow-y-auto">
      {trades.map((trade) => {
        const pnl = trade.payload?.pnl_usd || 0
        const isProfitable = pnl >= 0

        return (
          <div
            key={trade.id}
            className="flex items-center justify-between p-2 bg-slate-700/30 rounded"
          >
            <div className="flex items-center gap-3">
              <span
                className={`px-2 py-0.5 text-xs rounded ${
                  trade.payload?.direction === 'LONG'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-red-500/20 text-red-400'
                }`}
              >
                {trade.payload?.direction || 'N/A'}
              </span>
              <span className="text-sm">
                {trade.payload?.contracts || 1} @ {trade.payload?.fill_price?.toFixed(2) || '0.00'}
              </span>
            </div>
            <div className="flex items-center gap-4">
              <span
                className={`font-mono ${isProfitable ? 'text-emerald-400' : 'text-red-400'}`}
              >
                {isProfitable ? '+' : ''}{pnl.toFixed(2)}
              </span>
              <span className="text-xs text-slate-500">
                {format(new Date(trade.timestamp), 'HH:mm')}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
