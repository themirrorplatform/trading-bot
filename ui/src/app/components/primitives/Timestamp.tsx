/**
 * Timestamp - Consistent timestamp display component
 * Part of the trading cockpit primitive component library
 */

interface TimestampProps {
  value: string | Date;
  format?: 'full' | 'time' | 'relative';
  className?: string;
}

export function Timestamp({ value, format = 'full', className = '' }: TimestampProps) {
  const formatTimestamp = (val: string | Date) => {
    const date = typeof val === 'string' ? new Date(val) : val;
    
    if (format === 'time') {
      return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit',
        hour12: false 
      });
    }
    
    if (format === 'relative') {
      const now = new Date();
      const diff = now.getTime() - date.getTime();
      const seconds = Math.floor(diff / 1000);
      
      if (seconds < 60) return `${seconds}s ago`;
      if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
      if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
      return `${Math.floor(seconds / 86400)}d ago`;
    }
    
    return date.toLocaleString('en-US', { 
      month: 'short',
      day: 'numeric',
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit',
      hour12: false 
    });
  };

  return (
    <span className={`font-mono text-[0.75rem] text-[var(--text-2)] ${className}`}>
      {formatTimestamp(value)}
    </span>
  );
}
