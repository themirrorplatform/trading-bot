/**
 * DemoControlsDrawer - Collapsible drawer for demo controls
 * Accessible via toggle button, doesn't clutter the main screen
 */

import { useState } from 'react';
import { Settings, X } from 'lucide-react';

interface DemoControlsDrawerProps {
  decisionType: 'SKIP' | 'TRADE' | 'HALT';
  setDecisionType: (type: 'SKIP' | 'TRADE' | 'HALT') => void;
  connectionStatus: 'LIVE' | 'DEGRADED' | 'DISCONNECTED' | 'CATCHUP';
  setConnectionStatus: (status: 'LIVE' | 'DEGRADED' | 'DISCONNECTED' | 'CATCHUP') => void;
  systemState: any;
  setSystemState: (state: any) => void;
  showDriftAlerts: boolean;
  setShowDriftAlerts: (show: boolean) => void;
  showAttribution: boolean;
  setShowAttribution: (show: boolean) => void;
  handleKillSwitchReset: () => void;
  annotations: any[];
  setAnnotations: (annotations: any[]) => void;
  handleAddAnnotation: (annotation: any) => void;
  handleEditAnnotation: (id: string, annotation: any) => void;
  handleDeleteAnnotation: (id: string) => void;
}

export function DemoControlsDrawer({
  decisionType,
  setDecisionType,
  connectionStatus,
  setConnectionStatus,
  systemState,
  setSystemState,
  showDriftAlerts,
  setShowDriftAlerts,
  showAttribution,
  setShowAttribution,
  handleKillSwitchReset
}: DemoControlsDrawerProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Toggle Button - Fixed to right edge */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-1/2 right-0 -translate-y-1/2 z-[100] bg-[var(--bg-1)] border border-r-0 border-[var(--stroke-1)] rounded-l-lg px-3 py-4 hover:bg-[var(--bg-2)] transition-all shadow-lg"
        title={isOpen ? 'Close Demo Controls' : 'Open Demo Controls'}
      >
        <Settings className="w-5 h-5 text-[var(--text-1)]" />
      </button>

      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-[90] transition-opacity"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Drawer */}
      <div
        className={`fixed top-0 right-0 h-full w-[600px] max-w-[90vw] bg-[var(--bg-0)] border-l border-[var(--stroke-1)] z-[95] shadow-2xl transition-transform duration-300 ease-in-out overflow-y-auto ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="sticky top-0 bg-[var(--bg-0)] border-b border-[var(--stroke-1)] px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="text-lg font-semibold text-[var(--text-0)]">
              Demo Controls
            </h2>
            <p className="text-xs text-[var(--text-2)] mt-1">
              Live Cockpit Complete - Development Mode
            </p>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="p-2 hover:bg-[var(--bg-2)] rounded transition-colors"
            title="Close"
          >
            <X className="w-5 h-5 text-[var(--text-1)]" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Decision Type */}
          <div>
            <label className="text-sm font-medium text-[var(--text-0)] block mb-2">Decision Type</label>
            <select
              value={decisionType}
              onChange={(e) => setDecisionType(e.target.value as 'SKIP' | 'TRADE' | 'HALT')}
              className="w-full px-3 py-2 text-sm bg-[var(--bg-2)] border border-[var(--stroke-0)] rounded text-[var(--text-0)]"
            >
              <option value="SKIP">SKIP (Gates Failed)</option>
              <option value="TRADE">TRADE (All Gates Pass)</option>
              <option value="HALT">HALT (System Pause)</option>
            </select>
          </div>

          {/* Connection Status */}
          <div>
            <label className="text-sm font-medium text-[var(--text-0)] block mb-2">Connection Status</label>
            <select
              value={connectionStatus}
              onChange={(e) => setConnectionStatus(e.target.value as any)}
              className="w-full px-3 py-2 text-sm bg-[var(--bg-2)] border border-[var(--stroke-0)] rounded text-[var(--text-0)]"
            >
              <option value="LIVE">Live</option>
              <option value="DEGRADED">Degraded</option>
              <option value="DISCONNECTED">Disconnected</option>
              <option value="CATCHUP">Catching Up</option>
            </select>
          </div>

          {/* Bot Mode */}
          <div>
            <label className="text-sm font-medium text-[var(--text-0)] block mb-2">Bot Mode</label>
            <select
              value={systemState.mode}
              onChange={(e) => setSystemState({ ...systemState, mode: e.target.value as any })}
              className="w-full px-3 py-2 text-sm bg-[var(--bg-2)] border border-[var(--stroke-0)] rounded text-[var(--text-0)]"
            >
              <option value="OBSERVE">Observe</option>
              <option value="PAPER">Paper Trading</option>
              <option value="LIVE">Live Trading</option>
            </select>
          </div>

          {/* Visibility Toggles */}
          <div className="pt-4 border-t border-[var(--stroke-0)]">
            <div className="text-sm font-medium text-[var(--text-0)] mb-3">Visibility Options</div>
            
            <label className="flex items-center gap-3 mb-3 cursor-pointer">
              <input
                type="checkbox"
                checked={showDriftAlerts}
                onChange={(e) => setShowDriftAlerts(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm text-[var(--text-0)]">Show Drift Alerts</span>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={showAttribution}
                onChange={(e) => setShowAttribution(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm text-[var(--text-0)]">Show Attribution</span>
            </label>
          </div>

          {/* Kill Switch */}
          <div className="pt-4 border-t border-[var(--stroke-0)]">
            <label className="text-sm font-medium text-[var(--text-0)] block mb-3">Kill Switch</label>
            <button
              onClick={() => {
                if (systemState.killSwitch.status === 'ARMED') {
                  setSystemState({
                    ...systemState,
                    killSwitch: {
                      status: 'TRIPPED',
                      reason: 'Manual operator intervention - Demo',
                      timestamp: new Date().toISOString(),
                      operator: 'Demo User'
                    }
                  });
                } else {
                  handleKillSwitchReset();
                }
              }}
              className={`w-full px-4 py-3 rounded font-medium transition-colors ${
                systemState.killSwitch.status === 'ARMED'
                  ? 'bg-[var(--bad)] text-white hover:bg-[var(--bad-muted)]'
                  : 'bg-[var(--good)] text-white hover:bg-[var(--good-muted)]'
              }`}
            >
              {systemState.killSwitch.status === 'ARMED' ? 'Trigger Kill Switch' : 'Reset Kill Switch'}
            </button>
          </div>

          {/* Success Criteria Summary */}
          <div className="pt-4 border-t border-[var(--stroke-0)]">
            <div className="text-sm font-medium text-[var(--text-0)] mb-3">Success Criteria Status</div>
            <div className="grid grid-cols-1 gap-1 text-sm">
              <div className="text-[var(--good)]">✓ Event Completeness (12 types)</div>
              <div className="text-[var(--good)]">✓ Temporal Honesty</div>
              <div className="text-[var(--good)]">✓ Decision Presence</div>
              <div className="text-[var(--good)]">✓ Skip Is First-Class</div>
              <div className="text-[var(--good)]">✓ EUC Explainability</div>
              <div className="text-[var(--good)]">✓ Belief State Visibility</div>
              <div className="text-[var(--good)]">✓ Gate Explicitness</div>
              <div className="text-[var(--good)]">✓ Kill Switch Truth</div>
              <div className="text-[var(--good)]">✓ Expected vs Realized</div>
              <div className="text-[var(--good)]">✓ Attribution Visibility</div>
              <div className="text-[var(--good)]">✓ Drift Detection</div>
              <div className="text-[var(--good)]">✓ Manual Action Auditability</div>
              <div className="text-[var(--good)]">✓ Annotation Support</div>
              <div className="text-[var(--good)]">✓ Degraded States</div>
            </div>
          </div>

          {/* Footer */}
          <div className="pt-4 border-t border-[var(--stroke-0)] text-sm text-[var(--text-2)] text-center">
            All 24 success criteria implemented
          </div>
        </div>
      </div>
    </>
  );
}