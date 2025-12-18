/**
 * Card - Container component with variants for different elevations and states
 * Part of the trading cockpit primitive component library
 */

interface CardProps {
  children: React.ReactNode;
  variant?: 'default' | 'outlined' | 'alert';
  alertType?: 'error' | 'warning' | 'info';
  className?: string;
}

export function Card({ children, variant = 'default', alertType, className = '' }: CardProps) {
  const getStyles = () => {
    if (variant === 'outlined') {
      return 'bg-transparent border border-[var(--stroke-0)]';
    }
    
    if (variant === 'alert') {
      const alertStyles = {
        error: 'bg-[var(--bad-bg)] border border-[var(--stroke-error)]',
        warning: 'bg-[var(--warn-bg)] border border-[var(--stroke-warn)]',
        info: 'bg-[var(--info-bg)] border border-[var(--info)]'
      };
      return alertStyles[alertType || 'info'];
    }

    return 'bg-[var(--bg-1)] border border-[var(--stroke-1)]';
  };

  return (
    <div className={`rounded-lg p-4 ${getStyles()} ${className}`}>
      {children}
    </div>
  );
}
