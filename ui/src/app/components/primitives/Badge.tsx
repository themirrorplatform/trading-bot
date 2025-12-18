/**
 * Badge - Generic badge component for mode, session, severity indicators
 * Part of the trading cockpit primitive component library
 */

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'mode' | 'session' | 'severity' | 'delta' | 'neutral';
  type?: 'OBSERVE' | 'PAPER' | 'LIVE' | 'RTH' | 'ETH' | 'CRITICAL' | 'WARNING' | 'INFO' | 'POSITIVE' | 'NEGATIVE';
  className?: string;
}

export function Badge({ children, variant = 'neutral', type, className = '' }: BadgeProps) {
  const getStyles = () => {
    if (variant === 'mode') {
      const modeStyles = {
        OBSERVE: 'bg-[var(--info-bg)] border-[var(--info)] text-[var(--info)]',
        PAPER: 'bg-[var(--warn-bg)] border-[var(--warn)] text-[var(--warn)]',
        LIVE: 'bg-[var(--bad-bg)] border-[var(--bad)] text-[var(--bad)] animate-pulse'
      };
      return modeStyles[type as 'OBSERVE' | 'PAPER' | 'LIVE'] || modeStyles.OBSERVE;
    }

    if (variant === 'session') {
      return 'bg-[var(--bg-2)] border-[var(--stroke-0)] text-[var(--text-1)]';
    }

    if (variant === 'severity') {
      const severityStyles = {
        CRITICAL: 'bg-[var(--bad-bg)] border-[var(--stroke-error)] text-[var(--bad)]',
        WARNING: 'bg-[var(--warn-bg)] border-[var(--stroke-warn)] text-[var(--warn)]',
        INFO: 'bg-[var(--info-bg)] border-[var(--info)] text-[var(--info)]'
      };
      return severityStyles[type as 'CRITICAL' | 'WARNING' | 'INFO'] || severityStyles.INFO;
    }

    if (variant === 'delta') {
      const deltaStyles = {
        POSITIVE: 'bg-[var(--good-bg)] text-[var(--good)]',
        NEGATIVE: 'bg-[var(--bad-bg)] text-[var(--bad)]'
      };
      return deltaStyles[type as 'POSITIVE' | 'NEGATIVE'] || 'bg-[var(--neutral-bg)] text-[var(--text-2)]';
    }

    return 'bg-[var(--bg-2)] border-[var(--stroke-0)] text-[var(--text-1)]';
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-1 rounded-md border text-[0.6875rem] font-medium uppercase tracking-wide ${getStyles()} ${className}`}
    >
      {children}
    </span>
  );
}
