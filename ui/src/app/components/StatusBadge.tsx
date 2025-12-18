import React from 'react';
import { cn } from './ui/utils';

interface StatusBadgeProps {
  status: 'good' | 'warn' | 'bad' | 'info' | 'neutral';
  children: React.ReactNode;
  className?: string;
}

export function StatusBadge({ status, children, className }: StatusBadgeProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-medium',
        {
          'bg-[#1A7A45] text-[#2ED47A]': status === 'good',
          'bg-[#8B5A00] text-[#FFB020]': status === 'warn',
          'bg-[#8B2C2F] text-[#FF5A5F]': status === 'bad',
          'bg-[#285A8F] text-[#4DA3FF]': status === 'info',
          'bg-[#22304A] text-[#9AA9C2]': status === 'neutral',
        },
        className
      )}
    >
      {children}
    </div>
  );
}
