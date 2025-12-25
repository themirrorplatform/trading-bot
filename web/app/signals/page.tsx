import { createClient } from '@/lib/supabase/server'
import { SignalGauge } from '@/components/SignalGauge'

export const revalidate = 5

async function getLatestSignals() {
  const supabase = createClient()

  const { data } = await supabase
    .from('events')
    .select('*')
    .eq('event_type', 'BELIEFS_1M')
    .order('timestamp', { ascending: false })
    .limit(1)
    .single()

  return data?.payload || null
}

const SIGNAL_CATEGORIES = {
  'Price Structure': [
    { key: 'vwap_z', label: 'VWAP Z-Score', min: -3, max: 3 },
    { key: 'vwap_slope', label: 'VWAP Slope', min: -1, max: 1 },
    { key: 'atr_14_n', label: 'ATR(14) Normalized', min: 0, max: 2 },
    { key: 'range_compression', label: 'Range Compression', min: 0, max: 2 },
    { key: 'hhll_trend_strength', label: 'HHLL Trend', min: -1, max: 1 },
    { key: 'breakout_distance_n', label: 'Breakout Distance', min: -2, max: 2 },
  ],
  'Microstructure': [
    { key: 'rejection_wick_n', label: 'Rejection Wick', min: -1, max: 1 },
    { key: 'close_location_value', label: 'Close Location', min: 0, max: 1 },
    { key: 'gap_from_prev_close_n', label: 'Gap from Close', min: -2, max: 2 },
    { key: 'micro_trend_5', label: 'Micro Trend (5)', min: -1, max: 1 },
    { key: 'real_body_impulse_n', label: 'Body Impulse', min: 0, max: 3 },
  ],
  'Volume': [
    { key: 'vol_z', label: 'Volume Z-Score', min: -3, max: 3 },
    { key: 'vol_slope_20', label: 'Volume Slope', min: -1, max: 1 },
    { key: 'effort_vs_result', label: 'Effort vs Result', min: -1, max: 1 },
    { key: 'climax_bar_flag', label: 'Climax Bar', min: 0, max: 1 },
    { key: 'quiet_bar_flag', label: 'Quiet Bar', min: 0, max: 1 },
  ],
  'Session': [
    { key: 'session_phase', label: 'Session Phase', min: 0, max: 6 },
    { key: 'opening_range_break', label: 'OR Break', min: -1, max: 1 },
    { key: 'lunch_void_gate', label: 'Lunch Gate', min: 0, max: 1 },
    { key: 'close_magnet_index', label: 'Close Magnet', min: 0, max: 1 },
  ],
  'Quality': [
    { key: 'dvs', label: 'DVS', min: 0, max: 1 },
    { key: 'spread_proxy_tickiness', label: 'Spread Quality', min: 0, max: 1 },
    { key: 'slippage_risk_proxy', label: 'Slippage Risk', min: 0, max: 1 },
    { key: 'friction_regime_index', label: 'Friction Index', min: 0, max: 1 },
  ],
}

export default async function SignalsPage() {
  const signals = await getLatestSignals()

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Signal Monitor</h1>
        <div className="text-sm text-slate-400">
          Last update: {signals ? 'Just now' : 'No data'}
        </div>
      </div>

      {!signals ? (
        <div className="card text-center text-slate-500 py-12">
          No signal data available. Run the bot to generate signals.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Object.entries(SIGNAL_CATEGORIES).map(([category, categorySignals]) => (
            <div key={category} className="card">
              <h2 className="card-header">{category}</h2>
              <div className="space-y-4">
                {categorySignals.map((signal) => {
                  const value = (signals as any)[signal.key]
                  return (
                    <SignalGauge
                      key={signal.key}
                      label={signal.label}
                      value={value ?? 0}
                      min={signal.min}
                      max={signal.max}
                    />
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Constraint Beliefs */}
      <div className="card">
        <h2 className="card-header">Constraint Beliefs (Likelihoods)</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-4">
          {['F1', 'F3', 'F4', 'F5', 'F6'].map((constraint) => {
            const belief = signals ? (signals as any)[constraint] : null
            const likelihood = belief?.effective_likelihood ?? 0

            return (
              <div
                key={constraint}
                className={`text-center p-4 rounded-lg ${
                  likelihood >= 0.65
                    ? 'bg-emerald-500/20 border border-emerald-500/30'
                    : likelihood >= 0.5
                    ? 'bg-yellow-500/20 border border-yellow-500/30'
                    : 'bg-slate-700/50 border border-slate-600'
                }`}
              >
                <div className="text-lg font-bold">{constraint}</div>
                <div className="text-2xl font-mono mt-1">
                  {(likelihood * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  {constraint === 'F1' && 'VWAP MR'}
                  {constraint === 'F3' && 'Failed Break'}
                  {constraint === 'F4' && 'Sweep Rev'}
                  {constraint === 'F5' && 'Momentum'}
                  {constraint === 'F6' && 'Noise Filter'}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
