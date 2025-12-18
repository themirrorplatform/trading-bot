/**
 * SignalTile - Compact signal display with reliability and freshness
 * Part of the signals monitoring system
 */

import { NumericValue } from '../primitives/NumericValue';

interface SignalTileProps {
  signal: {
    name: string;
    value: number;
    reliability: number;
    freshness: 'FRESH' | 'STALE' | 'SUSPICIOUS';
    impact: number;
  };
  onClick?: () => void;
  className?: string;
}

export function SignalTile({ signal, onClick, className = '' }: SignalTileProps) {
  const freshnessStyles = {
    FRESH: 'border-[var(--stroke-good)]',
    STALE: 'border-[var(--stroke-warn)]',
    SUSPICIOUS: 'border-[var(--stroke-error)]'
  };

  const freshnessColors = {
    FRESH: 'text-[var(--good)]',
    STALE: 'text-[var(--warn)]',
    SUSPICIOUS: 'text-[var(--bad)]'
  };

  return (
    <div
      className={`p-3 rounded-lg border ${freshnessStyles[signal.freshness]} bg-[var(--bg-1)] hover:bg-[var(--bg-2)] transition-colors ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
    >
      {/* Signal Name */}
      <div className="text-xs text-[var(--text-2)] uppercase tracking-wide mb-2 truncate">
        {signal.name}
      </div>

      {/* Value */}
      <div className="font-mono text-lg text-[var(--text-0)] mb-3">
        <NumericValue value={signal.value} decimals={3} />
      </div>

      {/* Metrics */}
      <div className="space-y-2">
        {/* Reliability */}
        <div>
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-[var(--text-2)]">Reliability</span>
            <span className="font-mono text-[var(--text-1)]">
              <NumericValue value={signal.reliability} format="percentage" decimals={0} />
            </span>
          </div>
          <div className="h-1 bg-[var(--bg-3)] rounded overflow-hidden">
            <div
              className="h-full bg-[var(--good)]"
              style={{ width: `${signal.reliability * 100}%` }}
            />
          </div>
        </div>

        {/* Impact */}
        <div>
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-[var(--text-2)]">Impact</span>
            <span className="font-mono text-[var(--text-1)]">
              <NumericValue value={signal.impact} decimals={2} />
            </span>
          </div>
          <div className="h-1 bg-[var(--bg-3)] rounded overflow-hidden">
            <div
              className="h-full bg-[var(--accent)]"
              style={{ width: `${Math.min(Math.abs(signal.impact) * 100, 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Freshness Indicator */}
      <div className={`mt-2 text-xs font-medium ${freshnessColors[signal.freshness]}`}>
        {signal.freshness}
      </div>
    </div>
  );
}
