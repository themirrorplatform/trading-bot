/**
 * NumericValue - Displays numeric values with consistent formatting
 * Part of the trading cockpit primitive component library
 */

interface NumericValueProps {
  value: number;
  format?: 'decimal' | 'percentage' | 'currency' | 'integer';
  decimals?: number;
  delta?: boolean;
  className?: string;
}

export function NumericValue({ 
  value, 
  format = 'decimal', 
  decimals = 2,
  delta = false,
  className = '' 
}: NumericValueProps) {
  const formatValue = () => {
    // Handle NaN and Infinity
    if (!isFinite(value)) {
      return 'N/A';
    }
    
    switch (format) {
      case 'percentage':
        return `${(value * 100).toFixed(decimals)}%`;
      case 'currency':
        return `$${value.toFixed(decimals)}`;
      case 'integer':
        return Math.round(value).toLocaleString();
      default:
        return value.toFixed(decimals);
    }
  };

  const getDeltaStyle = () => {
    if (!delta) return '';
    if (value > 0) return 'text-[var(--good)]';
    if (value < 0) return 'text-[var(--bad)]';
    return 'text-[var(--text-2)]';
  };

  const getPrefix = () => {
    if (!delta) return '';
    if (value > 0) return '+';
    return '';
  };

  return (
    <span className={`font-mono tabular-nums ${getDeltaStyle()} ${className}`}>
      {getPrefix()}{formatValue()}
    </span>
  );
}