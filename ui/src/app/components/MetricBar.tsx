import React from 'react';
import { cn } from './ui/utils';

interface MetricBarProps {
  label: string;
  value: number;
  max: number;
  color: 'good' | 'warn' | 'bad' | 'info' | 'accent';
  showValue?: boolean;
  className?: string;
}

export function MetricBar({ label, value, max, color, showValue = true, className }: MetricBarProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
  
  const colorClasses = {
    good: 'bg-[#2ED47A]',
    warn: 'bg-[#FFB020]',
    bad: 'bg-[#FF5A5F]',
    info: 'bg-[#4DA3FF]',
    accent: 'bg-[#B38BFF]',
  };

  return (
    <div className={cn('space-y-1', className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-[#B8C7E0]">{label}</span>
        {showValue && (
          <span className="text-[#E7EEF9] font-mono tabular-nums">
            {value.toFixed(2)}
          </span>
        )}
      </div>
      <div className="h-2 bg-[#162033] rounded-full overflow-hidden">
        <div
          className={cn('h-full transition-all duration-300', colorClasses[color])}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
