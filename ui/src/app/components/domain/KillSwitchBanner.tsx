/**
 * KillSwitchBanner - Critical alert banner when kill switch is triggered
 * Cannot be dismissed, demands attention
 */

import { Badge } from '../primitives/Badge';
import { Timestamp } from '../primitives/Timestamp';

interface KillSwitchBannerProps {
  status: 'ARMED' | 'TRIPPED' | 'RESET_PENDING';
  reason?: string;
  timestamp?: string;
  operator?: string;
  onReset?: () => void;
}

export function KillSwitchBanner({ status, reason, timestamp, operator, onReset }: KillSwitchBannerProps) {
  if (status === 'ARMED') {
    return null;
  }

  return (
    <div className="bg-[var(--bad)] text-white p-4 animate-pulse">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <span className="text-lg font-bold uppercase tracking-wide">
              {status === 'TRIPPED' ? 'Kill Switch Activated' : 'Kill Switch Reset Pending'}
            </span>
          </div>

          {timestamp && (
            <div className="text-sm opacity-90">
              <Timestamp value={timestamp} />
            </div>
          )}
        </div>

        <div className="flex items-center gap-4">
          {reason && (
            <div className="text-sm">
              <span className="opacity-75">Reason:</span> {reason}
            </div>
          )}
          {operator && (
            <div className="text-sm">
              <span className="opacity-75">By:</span> {operator}
            </div>
          )}
          {status === 'RESET_PENDING' && onReset && (
            <button
              onClick={onReset}
              className="px-4 py-2 bg-white text-[var(--bad)] rounded font-medium hover:bg-gray-100 transition-colors"
            >
              Confirm Reset
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
