import React from 'react';
import { cn } from './ui/utils';

interface ReasonCodeChipProps {
  code: string;
  onClick?: () => void;
  className?: string;
}

export function ReasonCodeChip({ code, onClick, className }: ReasonCodeChipProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono',
        'bg-[#162033] text-[#B8C7E0] border border-[#22304A]',
        'hover:border-[#B38BFF] hover:text-[#B38BFF] transition-colors',
        onClick && 'cursor-pointer',
        className
      )}
    >
      {code}
    </button>
  );
}
