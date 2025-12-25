'use client'

import { format } from 'date-fns'

interface Decision {
  id: string
  timestamp: string
  payload: {
    action: string
    reason?: string
    metadata?: {
      template_id?: string
      euc_score?: number
      tier?: string
    }
  }
}

interface DecisionLogProps {
  decisions: Decision[]
}

const reasonLabels: Record<string, string> = {
  'NoTradeReason.DVS_TOO_LOW': 'DVS below threshold',
  'NoTradeReason.EQS_TOO_LOW': 'EQS below threshold',
  'NoTradeReason.SESSION_WINDOW_BLOCK': 'Lunch hour block',
  'NoTradeReason.SESSION_NOT_TRADABLE': 'Outside trading hours',
  'NoTradeReason.BELIEF_TOO_LOW': 'No strong setup',
  'NoTradeReason.EDGE_SCORE_BELOW_THETA': 'Edge too small',
  'NoTradeReason.KILL_SWITCH_ACTIVE': 'Kill switch triggered',
}

export function DecisionLog({ decisions }: DecisionLogProps) {
  if (decisions.length === 0) {
    return (
      <div className="text-center text-slate-500 py-8">
        No decisions yet
      </div>
    )
  }

  return (
    <div className="space-y-1 max-h-64 overflow-y-auto font-mono text-xs">
      {decisions.map((d) => {
        const isOrder = d.payload?.action === 'ORDER_INTENT'
        const reason = d.payload?.reason
        const reasonLabel = reason ? (reasonLabels[reason] || reason) : null

        return (
          <div
            key={d.id}
            className={`flex items-center gap-2 p-1.5 rounded ${
              isOrder ? 'bg-emerald-500/10' : 'bg-slate-700/30'
            }`}
          >
            <span className="text-slate-500 w-12">
              {format(new Date(d.timestamp), 'HH:mm')}
            </span>
            <span
              className={`w-16 ${isOrder ? 'text-emerald-400' : 'text-slate-400'}`}
            >
              {isOrder ? 'TRADE' : 'SKIP'}
            </span>
            <span className="text-slate-300 truncate flex-1">
              {isOrder
                ? `${d.payload?.metadata?.template_id} (EUC: ${d.payload?.metadata?.euc_score?.toFixed(2)})`
                : reasonLabel}
            </span>
          </div>
        )
      })}
    </div>
  )
}
