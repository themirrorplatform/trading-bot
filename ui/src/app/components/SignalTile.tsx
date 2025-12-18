import React from 'react';
import { cn } from './ui/utils';
import { StatusBadge } from './StatusBadge';
import { TrendingUp, TrendingDown } from 'lucide-react';
import type { Signal } from '../types/trading-types';

interface SignalTileProps {
  signal: Signal;
  onClick?: () => void;
  className?: string;
}

export function SignalTile({ signal, onClick, className }: SignalTileProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'OK':
        return 'good';
      case 'STALE':
        return 'warn';
      case 'SUSPICIOUS':
        return 'bad';
      default:
        return 'neutral';
    }
  };

  const getImpactLevel = (impact: number) => {
    if (impact > 7) return { level: 'High', color: 'good' };
    if (impact > 4) return { level: 'Medium', color: 'warn' };
    return { level: 'Low', color: 'neutral' };
  };

  const impactInfo = getImpactLevel(signal.impact_on_decision);

  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-[#111826] border border-[#22304A] rounded-xl p-4 space-y-3',
        'hover:border-[#B38BFF] transition-all cursor-pointer',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="text-xs font-mono text-[#B38BFF] truncate">
            {signal.signal_code}
          </div>
          <div className="text-sm text-[#E7EEF9] mt-0.5 truncate">
            {signal.signal_name}
          </div>
        </div>
        <StatusBadge status={getStatusColor(signal.status)} className="text-[10px]">
          {signal.status}
        </StatusBadge>
      </div>

      {/* Value */}
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-semibold text-[#E7EEF9] tabular-nums">
          {signal.current_value.toFixed(2)}
        </span>
        {signal.current_value > 0 ? (
          <TrendingUp className="w-4 h-4 text-[#2ED47A]" />
        ) : (
          <TrendingDown className="w-4 h-4 text-[#FF5A5F]" />
        )}
      </div>

      {/* Reliability Bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs">
          <span className="text-[#7F93B2]">Reliability</span>
          <span className="text-[#E7EEF9] font-mono tabular-nums">
            {(signal.reliability * 100).toFixed(0)}%
          </span>
        </div>
        <div className="h-1.5 bg-[#162033] rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full transition-all',
              signal.reliability > 0.8 ? 'bg-[#2ED47A]' : signal.reliability > 0.6 ? 'bg-[#FFB020]' : 'bg-[#FF5A5F]'
            )}
            style={{ width: `${signal.reliability * 100}%` }}
          />
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3 pt-2 border-t border-[#22304A]">
        <div>
          <div className="text-xs text-[#7F93B2]">Freshness</div>
          <div className="text-sm text-[#E7EEF9] tabular-nums">
            {signal.freshness_bars} bars
          </div>
        </div>
        <div>
          <div className="text-xs text-[#7F93B2]">Impact</div>
          <StatusBadge status={impactInfo.color as any} className="text-[10px] mt-1">
            {impactInfo.level}
          </StatusBadge>
        </div>
      </div>

      {/* Mini Sparkline */}
      <div className="h-8">
        <svg width="100%" height="100%" className="overflow-visible">
          <polyline
            fill="none"
            stroke="#B38BFF"
            strokeWidth="1.5"
            points={signal.history
              .map((val, i) => {
                const x = (i / (signal.history.length - 1)) * 100;
                const min = Math.min(...signal.history);
                const max = Math.max(...signal.history);
                const y = 100 - ((val - min) / (max - min)) * 100;
                return `${x},${y}`;
              })
              .join(' ')}
          />
        </svg>
      </div>
    </div>
  );
}
