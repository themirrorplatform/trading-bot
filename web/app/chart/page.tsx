'use client'

import { useEffect, useRef, useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { format } from 'date-fns'

interface Trade {
  timestamp: string
  price: number
  side: 'BUY' | 'SELL'
  pnl: number
  template_id?: string
}

export default function ChartPage() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)

  // Fetch today's trades for overlay
  useEffect(() => {
    async function fetchTrades() {
      const supabase = createClient()
      const today = new Date().toISOString().split('T')[0]

      const { data } = await supabase
        .from('events')
        .select('*')
        .eq('event_type', 'FILL_EVENT')
        .gte('timestamp', today)
        .order('timestamp', { ascending: true })

      if (data) {
        const parsed = data.map((e: any) => ({
          timestamp: e.timestamp,
          price: e.payload?.fill_price || e.payload?.entry_price || 0,
          side: e.payload?.side || (e.payload?.qty > 0 ? 'BUY' : 'SELL'),
          pnl: e.payload?.pnl_usd || 0,
          template_id: e.payload?.template_id,
        }))
        setTrades(parsed)
      }
      setLoading(false)
    }

    fetchTrades()
  }, [])

  // Load TradingView widget
  useEffect(() => {
    if (!containerRef.current) return

    // Clear previous widget
    containerRef.current.innerHTML = ''

    // Create TradingView widget
    const script = document.createElement('script')
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js'
    script.type = 'text/javascript'
    script.async = true
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: 'CME_MINI:MES1!',
      interval: '1',
      timezone: 'America/New_York',
      theme: 'dark',
      style: '1',
      locale: 'en',
      enable_publishing: false,
      hide_top_toolbar: false,
      hide_legend: false,
      save_image: true,
      calendar: false,
      hide_volume: false,
      support_host: 'https://www.tradingview.com',
      container_id: 'tradingview_chart',
      studies: [
        'MASimple@tv-basicstudies',
        'VWAP@tv-basicstudies',
      ],
    })

    const container = document.createElement('div')
    container.className = 'tradingview-widget-container'
    container.style.height = '100%'
    container.style.width = '100%'

    const innerContainer = document.createElement('div')
    innerContainer.id = 'tradingview_chart'
    innerContainer.style.height = 'calc(100% - 32px)'
    innerContainer.style.width = '100%'

    const copyright = document.createElement('div')
    copyright.className = 'tradingview-widget-copyright'
    copyright.innerHTML = '<a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank"><span class="text-xs text-slate-500">Track MES on TradingView</span></a>'

    container.appendChild(innerContainer)
    container.appendChild(copyright)
    container.appendChild(script)

    containerRef.current.appendChild(container)
  }, [])

  return (
    <div className="space-y-4 h-[calc(100vh-120px)]">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">MES Chart</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-slate-400">
            {trades.length} trades today
          </span>
          <a
            href="https://www.tradingview.com/chart/?symbol=CME_MINI:MES1!"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-400 hover:text-blue-300"
          >
            Open in TradingView ↗
          </a>
        </div>
      </div>

      {/* Trade List Overlay */}
      {trades.length > 0 && (
        <div className="bg-slate-800/80 rounded-lg p-3">
          <div className="text-sm font-medium mb-2">Today's Trades</div>
          <div className="flex gap-2 overflow-x-auto">
            {trades.map((trade, idx) => (
              <div
                key={idx}
                className={`flex-shrink-0 px-3 py-2 rounded text-sm ${
                  trade.pnl > 0
                    ? 'bg-emerald-500/20 border border-emerald-500/30'
                    : trade.pnl < 0
                    ? 'bg-red-500/20 border border-red-500/30'
                    : 'bg-slate-700'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className={trade.side === 'BUY' ? 'text-emerald-400' : 'text-red-400'}>
                    {trade.side}
                  </span>
                  <span className="font-mono">{trade.price.toFixed(2)}</span>
                  <span className={`font-medium ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {trade.pnl > 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                  </span>
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  {format(new Date(trade.timestamp), 'HH:mm:ss')}
                  {trade.template_id && ` • ${trade.template_id}`}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TradingView Chart */}
      <div
        ref={containerRef}
        className="bg-slate-900 rounded-lg flex-1"
        style={{ height: 'calc(100% - 80px)', minHeight: '400px' }}
      />

      {/* Chart Info */}
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div className="card p-3">
          <div className="text-slate-400">Symbol</div>
          <div className="font-bold">MES (Micro E-mini S&P 500)</div>
        </div>
        <div className="card p-3">
          <div className="text-slate-400">Tick Size</div>
          <div className="font-bold">0.25 pts ($1.25/tick)</div>
        </div>
        <div className="card p-3">
          <div className="text-slate-400">RTH Session</div>
          <div className="font-bold">09:30 - 16:00 ET</div>
        </div>
      </div>
    </div>
  )
}
