import React from 'react';
import { cn } from './ui/utils';
import { StatusBadge } from './StatusBadge';
import { X } from 'lucide-react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from './ui/sheet';
import { ScrollArea } from './ui/scroll-area';
import type { Signal } from '../types/trading-types';

interface SignalDetailPanelProps {
  signal: Signal | null;
  open: boolean;
  onClose: () => void;
}

export function SignalDetailPanel({ signal, open, onClose }: SignalDetailPanelProps) {
  if (!signal) return null;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'OK': return 'good';
      case 'STALE': return 'warn';
      case 'SUSPICIOUS': return 'bad';
      default: return 'neutral';
    }
  };

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-[480px] bg-[#0B0F14] border-l border-[#22304A] p-0">
        <SheetHeader className="px-6 py-4 border-b border-[#22304A]">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <SheetTitle className="text-[#E7EEF9]">{signal.signal_name}</SheetTitle>
              <div className="text-sm font-mono text-[#B38BFF] mt-1">{signal.signal_code}</div>
            </div>
            <button
              onClick={onClose}
              className="text-[#7F93B2] hover:text-[#E7EEF9] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-80px)]">
          <div className="px-6 py-6 space-y-6">
            {/* Status */}
            <div>
              <div className="text-xs text-[#7F93B2] mb-2">Status</div>
              <StatusBadge status={getStatusColor(signal.status)}>
                {signal.status}
              </StatusBadge>
            </div>

            {/* Current Value */}
            <div>
              <div className="text-xs text-[#7F93B2] mb-2">Current Value</div>
              <div className="text-3xl font-semibold text-[#E7EEF9] tabular-nums">
                {signal.current_value.toFixed(2)}
              </div>
            </div>

            {/* Reliability */}
            <div>
              <div className="text-xs text-[#7F93B2] mb-2">Reliability Score</div>
              <div className="space-y-2">
                <div className="text-xl font-semibold text-[#E7EEF9] tabular-nums">
                  {(signal.reliability * 100).toFixed(1)}%
                </div>
                <div className="h-2 bg-[#162033] rounded-full overflow-hidden">
                  <div
                    className={cn(
                      'h-full transition-all',
                      signal.reliability > 0.8 ? 'bg-[#2ED47A]' : signal.reliability > 0.6 ? 'bg-[#FFB020]' : 'bg-[#FF5A5F]'
                    )}
                    style={{ width: `${signal.reliability * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-[#111826] border border-[#22304A] rounded-lg p-4">
                <div className="text-xs text-[#7F93B2] mb-1">Freshness</div>
                <div className="text-lg font-semibold text-[#E7EEF9] tabular-nums">
                  {signal.freshness_bars} bars
                </div>
              </div>
              <div className="bg-[#111826] border border-[#22304A] rounded-lg p-4">
                <div className="text-xs text-[#7F93B2] mb-1">Impact on Decision</div>
                <div className="text-lg font-semibold text-[#E7EEF9] tabular-nums">
                  {signal.impact_on_decision.toFixed(1)}
                </div>
              </div>
            </div>

            {/* Category */}
            <div>
              <div className="text-xs text-[#7F93B2] mb-2">Category</div>
              <StatusBadge status="info">{signal.category}</StatusBadge>
            </div>

            {/* History Chart */}
            <div>
              <div className="text-xs text-[#7F93B2] mb-3">Last 50 Values</div>
              <div className="bg-[#111826] border border-[#22304A] rounded-lg p-4">
                <svg width="100%" height="120" className="overflow-visible">
                  {/* Grid lines */}
                  <line x1="0" y1="60" x2="100%" y2="60" stroke="#22304A" strokeWidth="1" strokeDasharray="2,2" />
                  
                  {/* Value line */}
                  <polyline
                    fill="none"
                    stroke="#B38BFF"
                    strokeWidth="2"
                    points={signal.history
                      .map((val, i) => {
                        const x = (i / (signal.history.length - 1)) * 100;
                        const min = Math.min(...signal.history);
                        const max = Math.max(...signal.history);
                        const range = max - min;
                        const y = range > 0 ? 100 - ((val - min) / range) * 80 + 10 : 60;
                        return `${x}%,${y}`;
                      })
                      .join(' ')}
                  />
                </svg>
                <div className="flex justify-between text-xs text-[#7F93B2] mt-2">
                  <span>-50 bars</span>
                  <span>Current</span>
                </div>
              </div>
            </div>

            {/* Exact Inputs */}
            <div>
              <div className="text-xs text-[#7F93B2] mb-2">Exact Inputs (Last Computation)</div>
              <div className="bg-[#111826] border border-[#22304A] rounded-lg p-4 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-[#7F93B2]">OHLC</span>
                  <span className="text-[#E7EEF9] font-mono">4565.00, 4568.00, 4564.50, 4567.25</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#7F93B2]">Volume</span>
                  <span className="text-[#E7EEF9] font-mono">1,234</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#7F93B2]">Session</span>
                  <span className="text-[#E7EEF9] font-mono">RTH</span>
                </div>
              </div>
            </div>

            {/* Normalization/Clipping */}
            <div>
              <div className="text-xs text-[#7F93B2] mb-2">Normalization</div>
              <div className="bg-[#111826] border border-[#22304A] rounded-lg p-4 text-xs text-[#B8C7E0]">
                Raw value: {(signal.current_value * 1.2).toFixed(2)} → Normalized: {signal.current_value.toFixed(2)}
                <br />
                Clipping: [-100, 100]
              </div>
            </div>

            {/* Which Constraints Feed */}
            <div>
              <div className="text-xs text-[#7F93B2] mb-2">Feeds These Constraints</div>
              <div className="space-y-2">
                {['C_MOMENTUM_REGIME', 'C_VOLATILITY_COMPRESSION', 'C_STRUCTURE_STRENGTH'].map((constraint, i) => (
                  <div
                    key={i}
                    className="bg-[#111826] border border-[#22304A] rounded-lg p-3 flex items-center justify-between"
                  >
                    <span className="text-sm text-[#E7EEF9] font-mono">{constraint}</span>
                    <span className="text-xs text-[#7F93B2] tabular-nums">
                      Weight: {(Math.random() * 0.5 + 0.3).toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Reliability History */}
            <div>
              <div className="text-xs text-[#7F93B2] mb-3">Reliability History</div>
              <div className="bg-[#111826] border border-[#22304A] rounded-lg p-4">
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-[#7F93B2]">10 bars ago</span>
                    <span className="text-[#E7EEF9]">0.75</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#7F93B2]">5 bars ago</span>
                    <span className="text-[#E7EEF9]">0.78</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#7F93B2]">Current</span>
                    <span className="text-[#2ED47A] font-semibold">{signal.reliability.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
