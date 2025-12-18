'use client'

import { useState } from 'react'

export default function SettingsPage() {
  const [killSwitch, setKillSwitch] = useState(false)

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* Kill Switch */}
      <div className="card">
        <h2 className="card-header">Emergency Controls</h2>
        <div className="flex items-center justify-between mt-4">
          <div>
            <h3 className="font-medium">Kill Switch</h3>
            <p className="text-sm text-slate-400">
              Immediately stop all trading and flatten positions
            </p>
          </div>
          <button
            onClick={() => setKillSwitch(!killSwitch)}
            className={`px-4 py-2 rounded font-medium transition-colors ${
              killSwitch
                ? 'bg-red-500 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            {killSwitch ? 'KILL ACTIVE' : 'Activate Kill'}
          </button>
        </div>
      </div>

      {/* Capital Tier */}
      <div className="card">
        <h2 className="card-header">Capital Configuration</h2>
        <div className="space-y-4 mt-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">
              Current Equity (USD)
            </label>
            <input
              type="number"
              defaultValue="1000"
              className="bg-slate-700 rounded px-3 py-2 w-full"
            />
          </div>
          <div className="flex gap-4 text-sm">
            <div className="flex-1 p-3 bg-slate-700/50 rounded">
              <div className="text-slate-400">Current Tier</div>
              <div className="text-xl font-bold text-yellow-400">S (Survival)</div>
            </div>
            <div className="flex-1 p-3 bg-slate-700/50 rounded">
              <div className="text-slate-400">Templates</div>
              <div className="text-xl font-bold">K1, K2</div>
            </div>
            <div className="flex-1 p-3 bg-slate-700/50 rounded">
              <div className="text-slate-400">Max Stop</div>
              <div className="text-xl font-bold">10 ticks</div>
            </div>
          </div>
          <p className="text-xs text-slate-500">
            Tier S: $0-$2.5k | Tier A: $2.5k-$7.5k | Tier B: $7.5k+
          </p>
        </div>
      </div>

      {/* Risk Limits */}
      <div className="card">
        <h2 className="card-header">Risk Limits</h2>
        <div className="grid grid-cols-2 gap-4 mt-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">
              Max Daily Loss (USD)
            </label>
            <input
              type="number"
              defaultValue="50"
              className="bg-slate-700 rounded px-3 py-2 w-full"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">
              Max Loss Per Trade (USD)
            </label>
            <input
              type="number"
              defaultValue="12"
              className="bg-slate-700 rounded px-3 py-2 w-full"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">
              Max Trades Per Day
            </label>
            <input
              type="number"
              defaultValue="8"
              className="bg-slate-700 rounded px-3 py-2 w-full"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">
              Consecutive Loss Lockout
            </label>
            <input
              type="number"
              defaultValue="3"
              className="bg-slate-700 rounded px-3 py-2 w-full"
            />
          </div>
        </div>
      </div>

      {/* Thresholds */}
      <div className="card">
        <h2 className="card-header">Quality Thresholds</h2>
        <div className="grid grid-cols-2 gap-4 mt-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">
              Min DVS
            </label>
            <input
              type="number"
              step="0.01"
              defaultValue="0.80"
              className="bg-slate-700 rounded px-3 py-2 w-full"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">
              Min EQS
            </label>
            <input
              type="number"
              step="0.01"
              defaultValue="0.75"
              className="bg-slate-700 rounded px-3 py-2 w-full"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">
              Min EUC Score
            </label>
            <input
              type="number"
              step="0.01"
              defaultValue="0.00"
              className="bg-slate-700 rounded px-3 py-2 w-full"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">
              Order TTL (seconds)
            </label>
            <input
              type="number"
              defaultValue="90"
              className="bg-slate-700 rounded px-3 py-2 w-full"
            />
          </div>
        </div>
      </div>

      {/* Connection */}
      <div className="card">
        <h2 className="card-header">Connection Status</h2>
        <div className="space-y-3 mt-4">
          <div className="flex items-center justify-between">
            <span>Supabase</span>
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 bg-emerald-400 rounded-full" />
              Connected
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span>Bot Backend</span>
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 bg-slate-400 rounded-full" />
              Not Running
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span>Tradovate</span>
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 bg-slate-400 rounded-full" />
              Disconnected
            </span>
          </div>
        </div>
      </div>

      <div className="flex gap-4">
        <button className="flex-1 bg-slate-700 hover:bg-slate-600 rounded py-2 font-medium">
          Reset to Defaults
        </button>
        <button className="flex-1 bg-emerald-600 hover:bg-emerald-500 rounded py-2 font-medium">
          Save Changes
        </button>
      </div>
    </div>
  )
}
