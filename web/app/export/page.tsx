'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { format } from 'date-fns'

type ExportType = 'trades' | 'decisions' | 'evolution' | 'signals' | 'all'
type ExportFormat = 'json' | 'csv'

export default function ExportPage() {
  const [loading, setLoading] = useState(false)
  const [dateRange, setDateRange] = useState({
    start: format(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), 'yyyy-MM-dd'),
    end: format(new Date(), 'yyyy-MM-dd'),
  })
  const [exportFormat, setExportFormat] = useState<ExportFormat>('json')

  async function fetchData(type: ExportType) {
    const supabase = createClient()
    const startDate = new Date(dateRange.start).toISOString()
    const endDate = new Date(dateRange.end + 'T23:59:59').toISOString()

    let eventTypes: string[] = []
    switch (type) {
      case 'trades':
        eventTypes = ['FILL_EVENT', 'ATTRIBUTION']
        break
      case 'decisions':
        eventTypes = ['DECISION_1M', 'DECISION_RECORD']
        break
      case 'evolution':
        eventTypes = ['EVOLUTION_REALTIME', 'EVOLUTION_FULL_TRADE', 'EVOLUTION_UPDATE', 'META_LEARNING_FREEZE']
        break
      case 'signals':
        eventTypes = ['BELIEFS_1M']
        break
      case 'all':
        eventTypes = []
        break
    }

    let query = supabase
      .from('events')
      .select('*')
      .gte('timestamp', startDate)
      .lte('timestamp', endDate)
      .order('timestamp', { ascending: true })

    if (eventTypes.length > 0) {
      query = query.in('event_type', eventTypes)
    }

    const { data, error } = await query.limit(10000)

    if (error) {
      throw new Error(error.message)
    }

    return data || []
  }

  function convertToCSV(data: any[]): string {
    if (data.length === 0) return ''

    // Flatten payload into columns
    const flattened = data.map(row => {
      const payload = row.payload || {}
      const flat: Record<string, any> = {
        id: row.id,
        stream_id: row.stream_id,
        timestamp: row.timestamp,
        event_type: row.event_type,
      }

      // Flatten payload keys
      Object.entries(payload).forEach(([key, value]) => {
        if (typeof value === 'object' && value !== null) {
          flat[`payload_${key}`] = JSON.stringify(value)
        } else {
          flat[`payload_${key}`] = value
        }
      })

      return flat
    })

    // Get all unique keys
    const allKeys = new Set<string>()
    flattened.forEach(row => Object.keys(row).forEach(k => allKeys.add(k)))
    const headers = Array.from(allKeys)

    // Build CSV
    const csvRows = [headers.join(',')]
    flattened.forEach(row => {
      const values = headers.map(h => {
        const val = row[h]
        if (val === undefined || val === null) return ''
        if (typeof val === 'string' && (val.includes(',') || val.includes('"') || val.includes('\n'))) {
          return `"${val.replace(/"/g, '""')}"`
        }
        return String(val)
      })
      csvRows.push(values.join(','))
    })

    return csvRows.join('\n')
  }

  async function handleExport(type: ExportType) {
    setLoading(true)
    try {
      const data = await fetchData(type)

      let content: string
      let filename: string
      let mimeType: string

      if (exportFormat === 'csv') {
        content = convertToCSV(data)
        filename = `trading-bot-${type}-${dateRange.start}-to-${dateRange.end}.csv`
        mimeType = 'text/csv'
      } else {
        content = JSON.stringify(data, null, 2)
        filename = `trading-bot-${type}-${dateRange.start}-to-${dateRange.end}.json`
        mimeType = 'application/json'
      }

      // Create download
      const blob = new Blob([content], { type: mimeType })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

    } catch (error) {
      alert(`Export failed: ${error}`)
    } finally {
      setLoading(false)
    }
  }

  async function handleExportParams() {
    setLoading(true)
    try {
      // Get latest evolution to get current params
      const supabase = createClient()
      const { data } = await supabase
        .from('events')
        .select('*')
        .in('event_type', ['EVOLUTION_REALTIME', 'EVOLUTION_FULL_TRADE', 'EVOLUTION_UPDATE'])
        .order('timestamp', { ascending: false })
        .limit(1)
        .single()

      const params = data?.payload || { message: 'No parameters found' }
      const content = JSON.stringify(params, null, 2)
      const filename = `trading-bot-params-${format(new Date(), 'yyyy-MM-dd-HHmm')}.json`

      const blob = new Blob([content], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

    } catch (error) {
      alert(`Export failed: ${error}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">Export Data</h1>

      {/* Date Range */}
      <div className="card">
        <h2 className="card-header">Date Range</h2>
        <div className="flex gap-4 mt-4">
          <div>
            <label className="text-sm text-slate-400 block mb-1">Start Date</label>
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
              className="bg-slate-700 rounded px-3 py-2"
            />
          </div>
          <div>
            <label className="text-sm text-slate-400 block mb-1">End Date</label>
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
              className="bg-slate-700 rounded px-3 py-2"
            />
          </div>
        </div>
      </div>

      {/* Format Selection */}
      <div className="card">
        <h2 className="card-header">Export Format</h2>
        <div className="flex gap-4 mt-4">
          <button
            onClick={() => setExportFormat('json')}
            className={`px-4 py-2 rounded ${exportFormat === 'json' ? 'bg-blue-600' : 'bg-slate-700 hover:bg-slate-600'}`}
          >
            JSON
          </button>
          <button
            onClick={() => setExportFormat('csv')}
            className={`px-4 py-2 rounded ${exportFormat === 'csv' ? 'bg-blue-600' : 'bg-slate-700 hover:bg-slate-600'}`}
          >
            CSV
          </button>
        </div>
      </div>

      {/* Export Buttons */}
      <div className="card">
        <h2 className="card-header">Download Data</h2>
        <div className="grid grid-cols-2 gap-4 mt-4">
          <button
            onClick={() => handleExport('trades')}
            disabled={loading}
            className="p-4 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 rounded-lg text-left"
          >
            <div className="font-bold">📊 Trades</div>
            <div className="text-sm text-emerald-200">Fill events & attribution</div>
          </button>

          <button
            onClick={() => handleExport('decisions')}
            disabled={loading}
            className="p-4 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600 rounded-lg text-left"
          >
            <div className="font-bold">🎯 Decisions</div>
            <div className="text-sm text-blue-200">Entry/skip decisions with reasons</div>
          </button>

          <button
            onClick={() => handleExport('evolution')}
            disabled={loading}
            className="p-4 bg-purple-600 hover:bg-purple-500 disabled:bg-slate-600 rounded-lg text-left"
          >
            <div className="font-bold">🧠 Learning History</div>
            <div className="text-sm text-purple-200">Evolution events & meta-learning</div>
          </button>

          <button
            onClick={() => handleExport('signals')}
            disabled={loading}
            className="p-4 bg-amber-600 hover:bg-amber-500 disabled:bg-slate-600 rounded-lg text-left"
          >
            <div className="font-bold">📈 Signal Snapshots</div>
            <div className="text-sm text-amber-200">All 28 signals over time</div>
          </button>

          <button
            onClick={() => handleExport('all')}
            disabled={loading}
            className="p-4 bg-slate-600 hover:bg-slate-500 disabled:bg-slate-700 rounded-lg text-left col-span-2"
          >
            <div className="font-bold">💾 Export Everything</div>
            <div className="text-sm text-slate-300">All event types in selected range</div>
          </button>
        </div>
      </div>

      {/* Current Parameters */}
      <div className="card">
        <h2 className="card-header">Current State</h2>
        <div className="mt-4">
          <button
            onClick={handleExportParams}
            disabled={loading}
            className="w-full p-4 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-600 rounded-lg text-left"
          >
            <div className="font-bold">⚙️ Current Parameters</div>
            <div className="text-sm text-indigo-200">Latest learned parameter values</div>
          </button>
        </div>
      </div>

      {loading && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
          <div className="bg-slate-800 p-6 rounded-lg">
            <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
            <div className="mt-4 text-center">Preparing download...</div>
          </div>
        </div>
      )}
    </div>
  )
}
