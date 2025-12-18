/**
 * EUCStackBar - Edge / Uncertainty / Cost visualization
 * Shows the three components of decision quality with threshold markers
 */

import { NumericValue } from '../primitives/NumericValue';

interface EUCStackBarProps {
  edge: number;
  uncertainty: number;
  cost: number;
  threshold: number;
  previousEUC?: number;
  className?: string;
}

export function EUCStackBar({ 
  edge, 
  uncertainty, 
  cost, 
  threshold,
  previousEUC,
  className = '' 
}: EUCStackBarProps) {
  const totalEUC = edge - uncertainty - cost;
  // Prevent division by zero - ensure maxValue is never 0
  const maxValue = Math.max(Math.abs(edge), Math.abs(uncertainty), Math.abs(cost), threshold, 0.0001) * 1.2;
  
  const getBarWidth = (value: number) => {
    return (Math.abs(value) / maxValue) * 100;
  };

  const delta = previousEUC !== undefined ? totalEUC - previousEUC : null;

  return (
    <div className={`space-y-3 ${className}`}>
      {/* EUC Components */}
      <div className="space-y-2">
        {/* Edge */}
        <div className="flex items-center gap-3">
          <span className="w-20 text-[0.75rem] text-[var(--text-2)] uppercase tracking-wide">Edge</span>
          <div className="flex-1 relative h-6 bg-[var(--bg-3)] rounded overflow-hidden">
            <div
              className="absolute left-0 top-0 h-full bg-[var(--good)] opacity-60"
              style={{ width: `${getBarWidth(edge)}%` }}
            />
            <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[0.75rem] font-mono text-[var(--text-0)] z-10">
              <NumericValue value={edge} decimals={4} />
            </span>
          </div>
        </div>

        {/* Uncertainty */}
        <div className="flex items-center gap-3">
          <span className="w-20 text-[0.75rem] text-[var(--text-2)] uppercase tracking-wide">Uncertainty</span>
          <div className="flex-1 relative h-6 bg-[var(--bg-3)] rounded overflow-hidden">
            <div
              className="absolute left-0 top-0 h-full bg-[var(--warn)] opacity-60"
              style={{ width: `${getBarWidth(uncertainty)}%` }}
            />
            <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[0.75rem] font-mono text-[var(--text-0)] z-10">
              <NumericValue value={uncertainty} decimals={4} />
            </span>
          </div>
        </div>

        {/* Cost */}
        <div className="flex items-center gap-3">
          <span className="w-20 text-[0.75rem] text-[var(--text-2)] uppercase tracking-wide">Cost</span>
          <div className="flex-1 relative h-6 bg-[var(--bg-3)] rounded overflow-hidden">
            <div
              className="absolute left-0 top-0 h-full bg-[var(--bad)] opacity-60"
              style={{ width: `${getBarWidth(cost)}%` }}
            />
            <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[0.75rem] font-mono text-[var(--text-0)] z-10">
              <NumericValue value={cost} decimals={4} />
            </span>
          </div>
        </div>
      </div>

      {/* Net EUC with threshold */}
      <div className="pt-2 border-t border-[var(--stroke-0)]">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[0.75rem] text-[var(--text-1)] uppercase tracking-wide">Net EUC</span>
          <div className="flex items-center gap-2">
            <span className={`font-mono ${totalEUC >= threshold ? 'text-[var(--good)]' : 'text-[var(--bad)]'}`}>
              <NumericValue value={totalEUC} decimals={4} />
            </span>
            {delta !== null && (
              <span className="text-[0.75rem]">
                <NumericValue value={delta} decimals={4} delta={true} />
              </span>
            )}
          </div>
        </div>
        <div className="relative h-8 bg-[var(--bg-3)] rounded overflow-hidden">
          {/* Threshold marker */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-[var(--accent)] z-10"
            style={{ left: `${(threshold / maxValue) * 100}%` }}
          />
          {/* Net EUC bar */}
          <div
            className={`absolute left-0 top-0 h-full ${
              totalEUC >= threshold ? 'bg-[var(--good)]' : 'bg-[var(--bad)]'
            } opacity-70`}
            style={{ width: `${getBarWidth(totalEUC)}%` }}
          />
          <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[0.6875rem] font-mono text-[var(--text-0)] z-10">
            Threshold: <NumericValue value={threshold} decimals={4} />
          </span>
        </div>
      </div>
    </div>
  );
}