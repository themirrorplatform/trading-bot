import { createClient } from '@/lib/supabase/server'
import { format } from 'date-fns'

export const revalidate = 10

async function getLearningData() {
  const supabase = createClient()

  // Get evolution events
  const { data: evolutionEvents } = await supabase
    .from('events')
    .select('*')
    .in('event_type', ['EVOLUTION_REALTIME', 'EVOLUTION_FULL_TRADE', 'EVOLUTION_UPDATE'])
    .order('timestamp', { ascending: false })
    .limit(50)

  // Get meta-learner freeze events
  const { data: freezeEvents } = await supabase
    .from('events')
    .select('*')
    .eq('event_type', 'META_LEARNING_FREEZE')
    .order('timestamp', { ascending: false })
    .limit(10)

  // Get attribution events for learning weight analysis
  const { data: attributionEvents } = await supabase
    .from('events')
    .select('*')
    .eq('event_type', 'ATTRIBUTION')
    .order('timestamp', { ascending: false })
    .limit(20)

  return {
    evolutionEvents: evolutionEvents || [],
    freezeEvents: freezeEvents || [],
    attributionEvents: attributionEvents || [],
  }
}

export default async function LearningPage() {
  const { evolutionEvents, freezeEvents, attributionEvents } = await getLearningData()

  // Calculate stats
  const totalEvolutions = evolutionEvents.length
  const avgParamsChanged = evolutionEvents.length > 0
    ? evolutionEvents.reduce((sum: number, e: any) => sum + (e.payload?.parameters_updated || 0), 0) / evolutionEvents.length
    : 0

  const decayedCount = evolutionEvents.reduce((sum: number, e: any) => sum + (e.payload?.decay_applied || 0), 0)

  // Group by learning direction
  const winsLearned = evolutionEvents.filter((e: any) => (e.payload?.pnl_usd || 0) > 0).length
  const lossesLearned = evolutionEvents.filter((e: any) => (e.payload?.pnl_usd || 0) < 0).length

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Learning & Evolution</h1>
        <div className="text-sm text-slate-400">
          Never Right Constitution Active
        </div>
      </div>

      {/* Never Right Constitution Stats */}
      <div className="card bg-gradient-to-br from-purple-500/10 to-blue-500/10 border border-purple-500/30">
        <h2 className="card-header flex items-center gap-2">
          <span className="text-purple-400">⚖️</span>
          Never Right Constitution
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-400">{winsLearned}</div>
            <div className="text-sm text-slate-400">Wins Learned</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-400">{lossesLearned}</div>
            <div className="text-sm text-slate-400">Losses Learned</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-amber-400">{decayedCount}</div>
            <div className="text-sm text-slate-400">Params Decayed</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold">0.75</div>
            <div className="text-sm text-slate-400">Max Confidence Cap</div>
          </div>
        </div>
        <div className="mt-4 p-3 bg-slate-800/50 rounded text-sm text-slate-400">
          <strong>Symmetric Learning:</strong> Wins and losses update parameters with equal magnitude.
          No success acceleration. Confidence decays toward neutral without confirmation.
        </div>
      </div>

      {/* Learning Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card text-center">
          <div className="text-3xl font-bold text-emerald-400">{totalEvolutions}</div>
          <div className="text-sm text-slate-400">Total Evolutions</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-blue-400">{avgParamsChanged.toFixed(1)}</div>
          <div className="text-sm text-slate-400">Avg Params/Trade</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-yellow-400">{freezeEvents.length}</div>
          <div className="text-sm text-slate-400">Learning Freezes</div>
        </div>
        <div className="card text-center">
          <div className={`text-3xl font-bold ${winsLearned === lossesLearned ? 'text-purple-400' : 'text-orange-400'}`}>
            {winsLearned === lossesLearned ? '✓' : '!'}
          </div>
          <div className="text-sm text-slate-400">Symmetry Check</div>
        </div>
      </div>

      {/* Evolution Event Log */}
      <div className="card">
        <h2 className="card-header">Evolution History</h2>
        <div className="space-y-3 mt-4 max-h-96 overflow-y-auto">
          {evolutionEvents.length === 0 ? (
            <div className="text-center text-slate-500 py-8">
              No evolution events yet. Complete trades to start learning.
            </div>
          ) : (
            evolutionEvents.map((event: any, idx: number) => {
              const pnl = event.payload?.pnl_usd || 0
              const paramsChanged = event.payload?.parameters_updated || 0
              const decayed = event.payload?.decay_applied || 0
              const changes = event.payload?.changes || {}

              return (
                <div
                  key={idx}
                  className={`p-3 rounded border-l-4 ${
                    pnl > 0
                      ? 'border-l-emerald-500 bg-emerald-500/5'
                      : pnl < 0
                      ? 'border-l-red-500 bg-red-500/5'
                      : 'border-l-slate-500 bg-slate-500/5'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <span className={`text-sm font-medium ${
                        pnl > 0 ? 'text-emerald-400' : pnl < 0 ? 'text-red-400' : 'text-slate-400'
                      }`}>
                        {pnl > 0 ? '+' : ''}{pnl.toFixed(2)} USD
                      </span>
                      <span className="text-slate-500 text-xs ml-2">
                        {event.event_type.replace('EVOLUTION_', '')}
                      </span>
                    </div>
                    <span className="text-xs text-slate-500">
                      {format(new Date(event.timestamp), 'MMM d HH:mm')}
                    </span>
                  </div>
                  <div className="flex gap-4 mt-2 text-xs text-slate-400">
                    <span>{paramsChanged} params learned</span>
                    <span>{decayed} params decayed</span>
                    <span>LW: {(event.payload?.learning_weight || 0).toFixed(2)}</span>
                  </div>
                  {Object.keys(changes).length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {Object.entries(changes).slice(0, 5).map(([key, val]: [string, any]) => (
                        <span
                          key={key}
                          className={`px-1.5 py-0.5 text-xs rounded ${
                            (val?.delta || 0) > 0
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : 'bg-red-500/20 text-red-400'
                          }`}
                        >
                          {key.split('.').pop()}: {(val?.delta || 0) > 0 ? '+' : ''}{(val?.delta || 0).toFixed(4)}
                        </span>
                      ))}
                      {Object.keys(changes).length > 5 && (
                        <span className="px-1.5 py-0.5 text-xs bg-slate-600 rounded">
                          +{Object.keys(changes).length - 5} more
                        </span>
                      )}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Learning Freezes */}
      {freezeEvents.length > 0 && (
        <div className="card border border-red-500/30">
          <h2 className="card-header text-red-400">Learning Freeze Events</h2>
          <div className="space-y-2 mt-4">
            {freezeEvents.map((event: any, idx: number) => (
              <div key={idx} className="p-3 bg-red-500/10 rounded">
                <div className="flex justify-between">
                  <span className="font-medium text-red-400">
                    {event.payload?.reason || 'Unknown'}
                  </span>
                  <span className="text-xs text-slate-500">
                    {format(new Date(event.timestamp), 'MMM d HH:mm')}
                  </span>
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  Drawdown: {((event.payload?.drawdown || 0) * 100).toFixed(1)}% |
                  Sharpe: {(event.payload?.sharpe || 0).toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Attribution Quality */}
      <div className="card">
        <h2 className="card-header">Attribution Quality (Last 20 Trades)</h2>
        <div className="grid grid-cols-5 gap-2 mt-4">
          {attributionEvents.map((event: any, idx: number) => {
            const lw = event.payload?.learning_weight || 0
            return (
              <div
                key={idx}
                className="text-center p-2 rounded"
                style={{
                  backgroundColor: `rgba(${lw > 0.5 ? '16, 185, 129' : '239, 68, 68'}, ${lw * 0.3})`,
                }}
              >
                <div className="text-lg font-mono">{(lw * 100).toFixed(0)}%</div>
                <div className="text-xs text-slate-500">LW</div>
              </div>
            )
          })}
          {attributionEvents.length === 0 && (
            <div className="col-span-5 text-center text-slate-500 py-4">
              No attribution data yet
            </div>
          )}
        </div>
        <div className="mt-3 text-xs text-slate-500">
          Learning Weight (LW) = how much the bot learns from each trade.
          Higher = more skill, less luck.
        </div>
      </div>
    </div>
  )
}
