/**
 * StatusChip - Displays gate evaluation status (PASS/FAIL/NA/ERROR)
 * Part of the trading cockpit primitive component library
 */

interface StatusChipProps {
  status: 'PASS' | 'FAIL' | 'NA' | 'ERROR';
  className?: string;
}

export function StatusChip({ status, className = '' }: StatusChipProps) {
  const variants = {
    PASS: {
      bg: 'bg-[var(--good-bg)]',
      border: 'border-[var(--stroke-good)]',
      text: 'text-[var(--good)]'
    },
    FAIL: {
      bg: 'bg-[var(--bad-bg)]',
      border: 'border-[var(--stroke-error)]',
      text: 'text-[var(--bad)]'
    },
    NA: {
      bg: 'bg-[var(--neutral-bg)]',
      border: 'border-[var(--stroke-0)]',
      text: 'text-[var(--text-2)]'
    },
    ERROR: {
      bg: 'bg-[var(--warn-bg)]',
      border: 'border-[var(--stroke-warn)]',
      text: 'text-[var(--warn)]'
    }
  };

  const variant = variants[status];

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md border ${variant.bg} ${variant.border} ${variant.text} text-[0.6875rem] font-medium uppercase tracking-wide ${className}`}
    >
      {status}
    </span>
  );
}
