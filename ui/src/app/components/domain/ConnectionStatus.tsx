/**
 * ConnectionStatus - Shows data connection health
 * Part of the system health monitoring
 */

import { Badge } from '../primitives/Badge';

interface ConnectionStatusProps {
  status: 'LIVE' | 'DEGRADED' | 'DISCONNECTED' | 'CATCHUP';
  latency?: number;
  lastUpdate?: string;
  className?: string;
}

export function ConnectionStatus({ status, latency, lastUpdate, className = '' }: ConnectionStatusProps) {
  const statusConfig = {
    LIVE: {
      color: 'text-[var(--good)]',
      bg: 'bg-[var(--good)]',
      label: 'Live'
    },
    DEGRADED: {
      color: 'text-[var(--warn)]',
      bg: 'bg-[var(--warn)]',
      label: 'Degraded'
    },
    DISCONNECTED: {
      color: 'text-[var(--bad)]',
      bg: 'bg-[var(--bad)]',
      label: 'Disconnected'
    },
    CATCHUP: {
      color: 'text-[var(--info)]',
      bg: 'bg-[var(--info)]',
      label: 'Catching Up'
    }
  };

  const config = statusConfig[status];

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className={`w-2 h-2 rounded-full ${config.bg} ${status === 'LIVE' ? 'animate-pulse' : ''}`} />
      <span className={`text-sm font-medium ${config.color}`}>
        {config.label}
      </span>
      {latency !== undefined && status === 'LIVE' && (
        <span className="text-xs text-[var(--text-2)] font-mono">
          {latency}ms
        </span>
      )}
    </div>
  );
}
