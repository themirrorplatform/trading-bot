/**
 * ReasonCodeChip - Displays reason codes with hover tooltip
 * Part of the trading cockpit primitive component library
 */

interface ReasonCodeChipProps {
  code: string;
  description?: string;
  className?: string;
}

export function ReasonCodeChip({ code, description, className = '' }: ReasonCodeChipProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded border border-[var(--stroke-0)] bg-[var(--bg-2)] text-[var(--accent)] text-[0.6875rem] font-mono hover:bg-[var(--bg-3)] transition-colors cursor-help ${className}`}
      title={description}
    >
      {code}
    </span>
  );
}
