import React from 'react';
import { cn } from './ui/utils';
import type { Severity } from '../types/trading-types';

interface SeverityDotProps {
  severity: Severity;
  className?: string;
}

export function SeverityDot({ severity, className }: SeverityDotProps) {
  return (
    <div
      className={cn(
        'w-2 h-2 rounded-full',
        {
          'bg-[#2ED47A]': severity === 'good',
          'bg-[#FFB020]': severity === 'warn',
          'bg-[#FF5A5F]': severity === 'bad',
          'bg-[#4DA3FF]': severity === 'info',
        },
        className
      )}
    />
  );
}
