/**
 * WhyNotCard - Explains why a trade was skipped
 * Shows blocking gates and what would need to change
 */

import { Card } from '../primitives/Card';
import { GateResultRow } from './GateResultRow';

interface WhyNotCardProps {
  blockingGates: Array<{
    name: string;
    status: 'PASS' | 'FAIL' | 'NA' | 'ERROR';
    required: number;
    actual: number;
    unit?: string;
    reasonCode?: string;
    reasonDescription?: string;
  }>;
  whatWouldChange: string[];
  className?: string;
}

export function WhyNotCard({ blockingGates, whatWouldChange, className = '' }: WhyNotCardProps) {
  if (blockingGates.length === 0) {
    return null;
  }

  return (
    <Card variant="outlined" className={className}>
      {/* Header */}
      <div className="mb-4">
        <h4 className="text-sm font-semibold text-[var(--text-0)] uppercase tracking-wide mb-1">
          Why This Trade Was Skipped
        </h4>
        <p className="text-xs text-[var(--text-2)]">
          {blockingGates.length} gate{blockingGates.length !== 1 ? 's' : ''} failed
        </p>
      </div>

      {/* Blocking Gates */}
      <div className="mb-4 rounded border border-[var(--stroke-0)] overflow-hidden">
        {blockingGates.map((gate, i) => (
          <GateResultRow key={i} gate={gate} />
        ))}
      </div>

      {/* What Would Need to Change */}
      {whatWouldChange.length > 0 && (
        <div>
          <div className="text-[0.6875rem] text-[var(--text-2)] uppercase tracking-wide mb-2">
            What Would Need to Change
          </div>
          <ul className="space-y-1">
            {whatWouldChange.map((change, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-[var(--text-1)]">
                <span className="text-[var(--accent)] flex-shrink-0">→</span>
                <span>{change}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
