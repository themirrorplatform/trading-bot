import React, { useState } from 'react';
import { cn } from './ui/utils';
import type { Constraint, Signal } from '../types/trading-types';

interface ConstraintSignalMatrixProps {
  constraints: Constraint[];
  signals: Signal[];
  onCellClick?: (constraint: Constraint, signal: Signal, weight: number) => void;
  className?: string;
}

export function ConstraintSignalMatrix({
  constraints,
  signals,
  onCellClick,
  className,
}: ConstraintSignalMatrixProps) {
  const [hoveredCell, setHoveredCell] = useState<{ constraintId: string; signalId: string } | null>(null);

  // Generate mock weights for the matrix (in real app, this would come from data)
  const getWeight = (constraint: Constraint, signal: Signal) => {
    // Mock: use hash of IDs to generate consistent pseudo-random weights
    const hash = (constraint.constraint_id + signal.signal_id).split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return (hash % 100) / 100 * signal.reliability;
  };

  const getColorForWeight = (weight: number) => {
    if (weight > 0.7) return 'bg-[#2ED47A]';
    if (weight > 0.5) return 'bg-[#4DA3FF]';
    if (weight > 0.3) return 'bg-[#B38BFF]';
    if (weight > 0.1) return 'bg-[#FFB020]';
    return 'bg-[#22304A]';
  };

  const getOpacityForWeight = (weight: number) => {
    return Math.max(0.2, weight);
  };

  // Take first 12 signals for display (to keep matrix readable)
  const displaySignals = signals.slice(0, 12);

  return (
    <div className={cn('overflow-auto', className)}>
      <div className="min-w-[800px]">
        {/* Header row */}
        <div className="grid grid-cols-[200px_repeat(12,1fr)] gap-px bg-[#22304A] border border-[#22304A] rounded-t-lg overflow-hidden">
          <div className="bg-[#111826] p-3"></div>
          {displaySignals.map((signal) => (
            <div
              key={signal.signal_id}
              className="bg-[#111826] p-3 text-xs text-[#7F93B2] writing-mode-vertical rotate-180"
              title={signal.signal_code}
            >
              <div className="transform rotate-180" style={{ writingMode: 'vertical-rl' }}>
                {signal.signal_code.substring(0, 15)}
              </div>
            </div>
          ))}
        </div>

        {/* Matrix rows */}
        {constraints.map((constraint, rowIndex) => (
          <div
            key={constraint.constraint_id}
            className={cn(
              'grid grid-cols-[200px_repeat(12,1fr)] gap-px bg-[#22304A]',
              rowIndex === constraints.length - 1 ? 'rounded-b-lg overflow-hidden' : ''
            )}
          >
            {/* Constraint label */}
            <div className="bg-[#111826] p-3 flex items-center">
              <div className="flex-1">
                <div className="text-sm text-[#E7EEF9] font-mono truncate">
                  {constraint.constraint_name}
                </div>
                <div className="text-xs text-[#7F93B2] tabular-nums">
                  P: {constraint.probability.toFixed(2)}
                </div>
              </div>
            </div>

            {/* Cells */}
            {displaySignals.map((signal) => {
              const weight = getWeight(constraint, signal);
              const isHovered = hoveredCell?.constraintId === constraint.constraint_id && hoveredCell?.signalId === signal.signal_id;

              return (
                <div
                  key={signal.signal_id}
                  className={cn(
                    'bg-[#111826] p-1 cursor-pointer transition-all relative',
                    isHovered && 'ring-2 ring-[#B38BFF]'
                  )}
                  onMouseEnter={() => setHoveredCell({ constraintId: constraint.constraint_id, signalId: signal.signal_id })}
                  onMouseLeave={() => setHoveredCell(null)}
                  onClick={() => onCellClick?.(constraint, signal, weight)}
                  title={`${constraint.constraint_name} ← ${signal.signal_code}\nWeight: ${weight.toFixed(3)}\nSignal: ${signal.current_value.toFixed(2)}`}
                >
                  <div
                    className={cn(
                      'w-full h-full rounded',
                      getColorForWeight(weight)
                    )}
                    style={{ opacity: getOpacityForWeight(weight) }}
                  />
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-4 flex items-center gap-4 text-xs text-[#7F93B2]">
        <span>Contribution Weight:</span>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 rounded bg-[#22304A]"></div>
            <span>None</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 rounded bg-[#FFB020]"></div>
            <span>Low</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 rounded bg-[#B38BFF]"></div>
            <span>Medium</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 rounded bg-[#4DA3FF]"></div>
            <span>High</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 rounded bg-[#2ED47A]"></div>
            <span>Very High</span>
          </div>
        </div>
      </div>
    </div>
  );
}
