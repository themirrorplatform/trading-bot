/**
 * GateResultRow - Individual gate evaluation result
 * Shows gate name, required threshold, actual value, and status
 */

import { StatusChip } from '../primitives/StatusChip';
import { NumericValue } from '../primitives/NumericValue';
import { ReasonCodeChip } from '../primitives/ReasonCodeChip';

interface GateResult {
  name: string;
  status: 'PASS' | 'FAIL' | 'NA' | 'ERROR';
  required: number;
  actual: number;
  unit?: string;
  reasonCode?: string;
  reasonDescription?: string;
}

interface GateResultRowProps {
  gate: GateResult;
  className?: string;
}

export function GateResultRow({ gate, className = '' }: GateResultRowProps) {
  return (
    <div className={`flex items-center gap-4 p-3 border-b border-[var(--stroke-1)] last:border-0 hover:bg-[var(--bg-2)] transition-colors ${className}`}>
      {/* Status */}
      <div className="flex-shrink-0">
        <StatusChip status={gate.status} />
      </div>

      {/* Gate Name */}
      <div className="flex-1 min-w-0">
        <div className="text-sm text-[var(--text-0)] truncate">
          {gate.name}
        </div>
      </div>

      {/* Values */}
      <div className="flex items-center gap-4 flex-shrink-0">
        <div className="text-right">
          <div className="text-[0.6875rem] text-[var(--text-2)] uppercase tracking-wide">
            Required
          </div>
          <div className="font-mono text-sm text-[var(--text-1)]">
            <NumericValue value={gate.required} decimals={gate.unit === '%' ? 1 : 2} />
            {gate.unit && <span className="ml-1">{gate.unit}</span>}
          </div>
        </div>

        <div className="text-right">
          <div className="text-[0.6875rem] text-[var(--text-2)] uppercase tracking-wide">
            Actual
          </div>
          <div className={`font-mono text-sm ${
            gate.status === 'PASS' ? 'text-[var(--good)]' : 
            gate.status === 'FAIL' ? 'text-[var(--bad)]' : 
            'text-[var(--text-1)]'
          }`}>
            <NumericValue value={gate.actual} decimals={gate.unit === '%' ? 1 : 2} />
            {gate.unit && <span className="ml-1">{gate.unit}</span>}
          </div>
        </div>
      </div>

      {/* Reason Code */}
      {gate.reasonCode && (
        <div className="flex-shrink-0">
          <ReasonCodeChip code={gate.reasonCode} description={gate.reasonDescription} />
        </div>
      )}
    </div>
  );
}
