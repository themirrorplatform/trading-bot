import React from 'react';
import { cn } from './ui/utils';

interface DeltaChipProps {
  expected: number;
  realized: number;
  unit?: string;
  className?: string;
}

export function DeltaChip({ expected, realized, unit = '', className }: DeltaChipProps) {
  const delta = realized - expected;
  const isPositive = delta > 0;
  const isNeutral = Math.abs(delta) < 0.01;

  return (
    <div className={cn('inline-flex items-center gap-2 text-xs', className)}>
      <span className="text-[#7F93B2]">
        Expected: <span className="text-[#B8C7E0] font-mono tabular-nums">{expected.toFixed(2)}{unit}</span>
      </span>
      <span className="text-[#7F93B2]">→</span>
      <span className="text-[#E7EEF9]">
        Realized: <span className="font-mono tabular-nums">{realized.toFixed(2)}{unit}</span>
      </span>
      {!isNeutral && (
        <span
          className={cn(
            'px-1.5 py-0.5 rounded font-mono tabular-nums',
            isPositive ? 'bg-[#1A7A45] text-[#2ED47A]' : 'bg-[#8B2C2F] text-[#FF5A5F]'
          )}
        >
          {isPositive ? '+' : ''}{delta.toFixed(2)}{unit}
        </span>
      )}
    </div>
  );
}
