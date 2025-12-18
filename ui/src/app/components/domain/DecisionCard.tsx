/**
 * DecisionCard - Shows current decision state (TRADE/SKIP/HALT) with full reasoning
 * The heart of the Live Cockpit - every decision must explain itself
 */

import { Card } from '../primitives/Card';
import { Badge } from '../primitives/Badge';
import { StatusChip } from '../primitives/StatusChip';
import { EUCStackBar } from './EUCStackBar';
import { NumericValue } from '../primitives/NumericValue';

interface Decision {
  type: 'TRADE' | 'SKIP' | 'HALT';
  timestamp: string;
  symbol: string;
  direction?: 'LONG' | 'SHORT';
  euc: {
    edge: number;
    uncertainty: number;
    cost: number;
    threshold: number;
    previous?: number;
  };
  capital: {
    tier: string;
    allocated: number;
    riskBudget: number;
  };
  template: string;
  expectedOutcome?: {
    probability: number;
    expectedValue: number;
    timeHorizon: string;
  };
  reasonCodes: string[];
}

interface DecisionCardProps {
  decision: Decision;
  className?: string;
}

export function DecisionCard({ decision, className = '' }: DecisionCardProps) {
  const typeStyles = {
    TRADE: {
      border: 'border-[var(--stroke-good)]',
      bg: 'bg-[var(--good-bg)]',
      text: 'text-[var(--good)]'
    },
    SKIP: {
      border: 'border-[var(--stroke-0)]',
      bg: 'bg-[var(--neutral-bg)]',
      text: 'text-[var(--text-1)]'
    },
    HALT: {
      border: 'border-[var(--stroke-error)]',
      bg: 'bg-[var(--bad-bg)]',
      text: 'text-[var(--bad)]'
    }
  };

  const style = typeStyles[decision.type];

  return (
    <Card className={`border-2 ${style.border} ${className}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className={`text-lg font-semibold ${style.text}`}>
              {decision.type}
            </h3>
            {decision.direction && (
              <Badge variant="neutral">
                {decision.direction}
              </Badge>
            )}
          </div>
          <div className="text-[var(--text-2)] text-sm">
            {decision.symbol} • {new Date(decision.timestamp).toLocaleTimeString()}
          </div>
        </div>
        <Badge variant="neutral">
          {decision.template}
        </Badge>
      </div>

      {/* EUC Stack */}
      <div className="mb-4">
        <EUCStackBar
          edge={decision.euc.edge}
          uncertainty={decision.euc.uncertainty}
          cost={decision.euc.cost}
          threshold={decision.euc.threshold}
          previousEUC={decision.euc.previous}
        />
      </div>

      {/* Capital Allocation */}
      <div className="grid grid-cols-3 gap-4 mb-4 p-3 bg-[var(--bg-2)] rounded border border-[var(--stroke-0)]">
        <div>
          <div className="text-[0.6875rem] text-[var(--text-2)] uppercase tracking-wide mb-1">
            Capital Tier
          </div>
          <div className="font-mono text-[var(--text-0)]">
            {decision.capital.tier}
          </div>
        </div>
        <div>
          <div className="text-[0.6875rem] text-[var(--text-2)] uppercase tracking-wide mb-1">
            Allocated
          </div>
          <div className="font-mono text-[var(--text-0)]">
            <NumericValue value={decision.capital.allocated} format="currency" decimals={0} />
          </div>
        </div>
        <div>
          <div className="text-[0.6875rem] text-[var(--text-2)] uppercase tracking-wide mb-1">
            Risk Budget
          </div>
          <div className="font-mono text-[var(--text-0)]">
            <NumericValue value={decision.capital.riskBudget} format="percentage" decimals={1} />
          </div>
        </div>
      </div>

      {/* Expected Outcome (for TRADE decisions) */}
      {decision.expectedOutcome && (
        <div className="mb-4 p-3 bg-[var(--bg-2)] rounded border border-[var(--stroke-0)]">
          <div className="text-[0.6875rem] text-[var(--text-2)] uppercase tracking-wide mb-2">
            Expected Outcome
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <div className="text-[var(--text-2)] text-xs">Probability</div>
              <div className="font-mono text-[var(--text-0)]">
                <NumericValue value={decision.expectedOutcome.probability} format="percentage" />
              </div>
            </div>
            <div>
              <div className="text-[var(--text-2)] text-xs">Expected Value</div>
              <div className="font-mono text-[var(--text-0)]">
                <NumericValue value={decision.expectedOutcome.expectedValue} format="currency" />
              </div>
            </div>
            <div>
              <div className="text-[var(--text-2)] text-xs">Time Horizon</div>
              <div className="font-mono text-[var(--text-0)]">
                {decision.expectedOutcome.timeHorizon}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reason Codes */}
      <div>
        <div className="text-[0.6875rem] text-[var(--text-2)] uppercase tracking-wide mb-2">
          Reason Codes
        </div>
        <div className="flex flex-wrap gap-2">
          {decision.reasonCodes.map((code, i) => (
            <span
              key={i}
              className="px-2 py-1 text-xs font-mono bg-[var(--bg-3)] border border-[var(--stroke-0)] rounded text-[var(--accent)]"
            >
              {code}
            </span>
          ))}
        </div>
      </div>
    </Card>
  );
}
