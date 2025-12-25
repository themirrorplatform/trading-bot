import { StatusCard } from '@/components/StatusCard'
import { EquityCurve } from '@/components/EquityCurve'
import { RecentTrades } from '@/components/RecentTrades'
import { SignalGauge } from '@/components/SignalGauge'
import { DecisionLog } from '@/components/DecisionLog'
import { createClient } from '@/lib/supabase/server'

export const revalidate = 5 // Revalidate every 5 seconds

async function getDashboardData() {
  const supabase = createClient()

  // Get latest bot state
  const { data: latestDecision } = await supabase
    .from('events')
    .select('*')
    .eq('event_type', 'DECISION_1M')
    .order('timestamp', { ascending: false })
    .limit(1)
    .single()

  // Get today's trades
  const today = new Date().toISOString().split('T')[0]
  const { data: todayTrades } = await supabase
    .from('events')
    .select('*')
    .eq('event_type', 'FILL_EVENT')
    .gte('timestamp', today)
    .order('timestamp', { ascending: false })

  // Get recent decisions for log
  const { data: recentDecisions } = await supabase
    .from('events')
    .select('*')
    .eq('event_type', 'DECISION_1M')
    .order('timestamp', { ascending: false })
    .limit(20)

  return {
    latestDecision: latestDecision?.payload || null,
    todayTrades: todayTrades || [],
    recentDecisions: recentDecisions || [],
  }
}

export default async function Dashboard() {
  const { latestDecision, todayTrades, recentDecisions } = await getDashboardData()

  // Calculate daily P&L
  const dailyPnL = todayTrades.reduce((sum: number, t: any) =>
    sum + (t.payload?.pnl_usd || 0), 0)

  const winCount = todayTrades.filter((t: any) => (t.payload?.pnl_usd || 0) > 0).length
  const winRate = todayTrades.length > 0 ? (winCount / todayTrades.length) * 100 : 0

  return (
    <div className="space-y-6">
      {/* Status Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatusCard
          title="Bot Status"
          value={latestDecision ? "RUNNING" : "OFFLINE"}
          status={latestDecision ? "success" : "error"}
        />
        <StatusCard
          title="Daily P&L"
          value={`$${dailyPnL.toFixed(2)}`}
          status={dailyPnL >= 0 ? "success" : "error"}
        />
        <StatusCard
          title="Trades Today"
          value={todayTrades.length.toString()}
          status="neutral"
        />
        <StatusCard
          title="Win Rate"
          value={`${winRate.toFixed(0)}%`}
          status={winRate >= 50 ? "success" : "warning"}
        />
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Equity Curve */}
        <div className="lg:col-span-2 card">
          <h2 className="card-header">Equity Curve</h2>
          <EquityCurve />
        </div>

        {/* Signal Gauges */}
        <div className="card">
          <h2 className="card-header">Current Signals</h2>
          <div className="space-y-4">
            <SignalGauge
              label="VWAP Z-Score"
              value={latestDecision?.signals?.vwap_z || 0}
              min={-3}
              max={3}
            />
            <SignalGauge
              label="ATR (14) Normalized"
              value={latestDecision?.signals?.atr_14_n || 1}
              min={0}
              max={2}
            />
            <SignalGauge
              label="Volume Z-Score"
              value={latestDecision?.signals?.vol_z || 0}
              min={-3}
              max={3}
            />
            <SignalGauge
              label="DVS"
              value={latestDecision?.dvs || 1}
              min={0}
              max={1}
            />
            <SignalGauge
              label="EQS"
              value={latestDecision?.eqs || 1}
              min={0}
              max={1}
            />
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Trades */}
        <div className="card">
          <h2 className="card-header">Recent Trades</h2>
          <RecentTrades trades={todayTrades} />
        </div>

        {/* Decision Log */}
        <div className="card">
          <h2 className="card-header">Decision Log</h2>
          <DecisionLog decisions={recentDecisions} />
        </div>
      </div>
    </div>
  )
}
