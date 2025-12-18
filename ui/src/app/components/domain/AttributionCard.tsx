/**
 * AttributionCard - Attribution V2 display
 * Shows edge/luck/execution contribution for closed trades
 */

import { Card } from '../primitives/Card';
import { NumericValue } from '../primitives/NumericValue';
import { Timestamp } from '../primitives/Timestamp';

interface Attribution {
  tradeId: string;
  closedAt: string;
  totalPnL: number;
  edgeContribution: number;
  luckContribution: number;
  executionContribution: number;
  learningWeight: number;
  expectedPnL: number;
  realizedPnL: number;
  classification: 'EDGE_WIN' | 'EDGE_LOSS' | 'LUCKY_WIN' | 'UNLUCKY_LOSS' | 'EXECUTION_WIN' | 'EXECUTION_LOSS';
}

interface AttributionCardProps {
  attribution: Attribution;
  className?: string;
}

export function AttributionCard({ attribution, className = '' }: AttributionCardProps) {
  const total = Math.abs(attribution.edgeContribution) + 
                Math.abs(attribution.luckContribution) + 
                Math.abs(attribution.executionContribution);
  
  // Prevent division by zero if all contributions are exactly 0
  const safeTotal = total === 0 ? 1 : total;

  const getClassificationColor = (classification: string) => {
    if (classification.includes('WIN')) return 'text-[var(--good)]';
    if (classification.includes('LOSS')) return 'text-[var(--bad)]';
    return 'text-[var(--text-1)]';
  };

  return (
    <Card className={className}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h4 className="text-sm font-semibold text-[var(--text-0)] mb-1">
            Attribution Analysis
          </h4>
          <div className="text-xs text-[var(--text-2)]">
            Trade {attribution.tradeId} • <Timestamp value={attribution.closedAt} />
          </div>
        </div>
        <span className={`text-sm font-medium ${getClassificationColor(attribution.classification)}`}>
          {attribution.classification.replace(/_/g, ' ')}
        </span>
      </div>

      {/* PnL Comparison */}
      <div className="grid grid-cols-2 gap-4 mb-4 p-3 bg-[var(--bg-2)] rounded">
        <div>
          <div className="text-xs text-[var(--text-2)] mb-1">Expected PnL</div>
          <div className="font-mono text-[var(--text-0)]">
            <NumericValue value={attribution.expectedPnL} format="currency" delta={false} />
          </div>
        </div>
        <div>
          <div className="text-xs text-[var(--text-2)] mb-1">Realized PnL</div>
          <div className="font-mono">
            <NumericValue value={attribution.realizedPnL} format="currency" delta={true} />
          </div>
        </div>
      </div>

      {/* Attribution Breakdown */}
      <div className="space-y-3">
        {/* Edge Contribution */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-[var(--text-2)] uppercase tracking-wide">
              Edge Contribution
            </span>
            <span className="font-mono text-sm">
              <NumericValue value={attribution.edgeContribution} format="currency" delta={true} />
            </span>
          </div>
          <div className="h-2 bg-[var(--bg-3)] rounded overflow-hidden">
            <div
              className={`h-full ${attribution.edgeContribution >= 0 ? 'bg-[var(--good)]' : 'bg-[var(--bad)]'}`}
              style={{ width: `${(Math.abs(attribution.edgeContribution) / safeTotal) * 100}%` }}
            />
          </div>
        </div>

        {/* Luck Contribution */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-[var(--text-2)] uppercase tracking-wide">
              Luck Contribution
            </span>
            <span className="font-mono text-sm">
              <NumericValue value={attribution.luckContribution} format="currency" delta={true} />
            </span>
          </div>
          <div className="h-2 bg-[var(--bg-3)] rounded overflow-hidden">
            <div
              className="h-full bg-[var(--neutral)]"
              style={{ width: `${(Math.abs(attribution.luckContribution) / safeTotal) * 100}%` }}
            />
          </div>
        </div>

        {/* Execution Contribution */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-[var(--text-2)] uppercase tracking-wide">
              Execution Contribution
            </span>
            <span className="font-mono text-sm">
              <NumericValue value={attribution.executionContribution} format="currency" delta={true} />
            </span>
          </div>
          <div className="h-2 bg-[var(--bg-3)] rounded overflow-hidden">
            <div
              className={`h-full ${attribution.executionContribution >= 0 ? 'bg-[var(--good)]' : 'bg-[var(--bad)]'}`}
              style={{ width: `${(Math.abs(attribution.executionContribution) / safeTotal) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Learning Weight */}
      <div className="mt-4 pt-4 border-t border-[var(--stroke-0)]">
        <div className="flex items-center justify-between">
          <span className="text-xs text-[var(--text-2)] uppercase tracking-wide">
            Learning Weight
          </span>
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm text-[var(--text-0)]">
              <NumericValue value={attribution.learningWeight} format="percentage" decimals={1} />
            </span>
            {attribution.learningWeight === 0 && (
              <span className="text-xs text-[var(--warn)]">(Suppressed)</span>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}