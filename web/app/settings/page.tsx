import { createClient } from '@/lib/supabase/server'

export const revalidate = 10 // Refresh every 10 seconds

async function getBotConfig() {
  const supabase = createClient()

  // Get latest system event to check bot status
  const { data: systemEvent } = await supabase
    .from('events')
    .select('*')
    .eq('event_type', 'SYSTEM_EVENT')
    .order('timestamp', { ascending: false })
    .limit(1)
    .single()

  // Get latest decision to check if bot is running
  const { data: latestDecision } = await supabase
    .from('events')
    .select('*')
    .eq('event_type', 'DECISION_1M')
    .order('timestamp', { ascending: false })
    .limit(1)
    .single()

  return {
    systemEvent: systemEvent?.payload || null,
    latestDecision: latestDecision?.payload || null,
    lastActivity: latestDecision?.timestamp || null,
  }
}

export default async function SettingsPage() {
  const { systemEvent, latestDecision, lastActivity } = await getBotConfig()

  // Check if bot has been active in last 5 minutes
  const isRecentlyActive = lastActivity
    ? new Date().getTime() - new Date(lastActivity).getTime() < 5 * 60 * 1000
    : false

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">Bot Configuration</h1>

      {/* Read-Only Notice */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <svg className="w-5 h-5 text-blue-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h3 className="font-medium text-blue-400">Read-Only Dashboard</h3>
            <p className="text-sm text-slate-400 mt-1">
              This dashboard displays bot status but cannot control the bot.
              To modify settings, edit the YAML contracts or use CLI commands on the machine running the bot.
            </p>
          </div>
        </div>
      </div>

      {/* Bot Status */}
      <div className="card">
        <h2 className="card-header">Bot Status</h2>
        <div className="space-y-3 mt-4">
          <div className="flex items-center justify-between">
            <span>Trading Bot</span>
            <span className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${isRecentlyActive ? 'bg-emerald-400' : 'bg-slate-400'}`} />
              {isRecentlyActive ? 'Active' : 'Inactive'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span>Last Activity</span>
            <span className="text-slate-400">
              {lastActivity ? new Date(lastActivity).toLocaleString() : 'No data'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span>Supabase Sync</span>
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 bg-emerald-400 rounded-full" />
              Connected
            </span>
          </div>
        </div>
      </div>

      {/* Capital Tier (Read-Only Display) */}
      <div className="card">
        <h2 className="card-header">Capital Tiers</h2>
        <div className="space-y-4 mt-4">
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="p-3 bg-slate-700/50 rounded border-l-2 border-yellow-400">
              <div className="text-slate-400">Tier S</div>
              <div className="font-bold">$0 - $2.5k</div>
              <div className="text-xs text-slate-500 mt-1">Templates: K1, K2</div>
            </div>
            <div className="p-3 bg-slate-700/50 rounded border-l-2 border-blue-400">
              <div className="text-slate-400">Tier A</div>
              <div className="font-bold">$2.5k - $7.5k</div>
              <div className="text-xs text-slate-500 mt-1">Templates: K1-K3</div>
            </div>
            <div className="p-3 bg-slate-700/50 rounded border-l-2 border-emerald-400">
              <div className="text-slate-400">Tier B</div>
              <div className="font-bold">$7.5k+</div>
              <div className="text-xs text-slate-500 mt-1">Templates: K1-K4</div>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Limits (Read-Only Display) */}
      <div className="card">
        <h2 className="card-header">Risk Limits (from risk_model.yaml)</h2>
        <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
          <div className="p-3 bg-slate-700/30 rounded">
            <div className="text-slate-400">Max Daily Loss</div>
            <div className="font-bold">$50</div>
          </div>
          <div className="p-3 bg-slate-700/30 rounded">
            <div className="text-slate-400">Max Loss Per Trade</div>
            <div className="font-bold">$12 (Tier S)</div>
          </div>
          <div className="p-3 bg-slate-700/30 rounded">
            <div className="text-slate-400">Max Trades Per Day</div>
            <div className="font-bold">8</div>
          </div>
          <div className="p-3 bg-slate-700/30 rounded">
            <div className="text-slate-400">Consecutive Loss Lockout</div>
            <div className="font-bold">3</div>
          </div>
        </div>
      </div>

      {/* Quality Thresholds (Read-Only Display) */}
      <div className="card">
        <h2 className="card-header">Quality Thresholds</h2>
        <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
          <div className="p-3 bg-slate-700/30 rounded">
            <div className="text-slate-400">Min DVS (Data Quality)</div>
            <div className="font-bold">0.80</div>
          </div>
          <div className="p-3 bg-slate-700/30 rounded">
            <div className="text-slate-400">Min EQS (Execution Quality)</div>
            <div className="font-bold">0.75</div>
          </div>
          <div className="p-3 bg-slate-700/30 rounded">
            <div className="text-slate-400">Min EUC Score</div>
            <div className="font-bold">0.00</div>
          </div>
          <div className="p-3 bg-slate-700/30 rounded">
            <div className="text-slate-400">Order TTL</div>
            <div className="font-bold">90 seconds</div>
          </div>
        </div>
      </div>

      {/* CLI Commands Reference */}
      <div className="card">
        <h2 className="card-header">Control Commands (Run on Bot Machine)</h2>
        <div className="mt-4 space-y-3 font-mono text-sm">
          <div className="p-2 bg-slate-800 rounded">
            <span className="text-slate-400"># Start live trading</span>
            <br />
            python -m trading_bot live --environment demo
          </div>
          <div className="p-2 bg-slate-800 rounded">
            <span className="text-slate-400"># Activate kill switch</span>
            <br />
            python -m trading_bot kill --reason "manual stop"
          </div>
          <div className="p-2 bg-slate-800 rounded">
            <span className="text-slate-400"># Check status</span>
            <br />
            python -m trading_bot status
          </div>
          <div className="p-2 bg-slate-800 rounded">
            <span className="text-slate-400"># Run evolution (learn from trades)</span>
            <br />
            python -m trading_bot evolve --force
          </div>
        </div>
      </div>
    </div>
  )
}
