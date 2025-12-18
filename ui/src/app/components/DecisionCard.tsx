import React from 'react';
import { cn } from './ui/utils';
import { StatusBadge } from './StatusBadge';
import { MetricBar } from './MetricBar';
import type { DecisionRecord } from '../types/trading-types';

interface DecisionCardProps {
  decision: DecisionRecord | null;
  className?: string;
}

export function DecisionCard({ decision, className }: DecisionCardProps) {
  if (!decision) {
    return (
      <div className={cn('bg-[#111826] border border-[#22304A] rounded-xl p-6', className)}>
        <div className="text-center text-[#7F93B2] py-8">
          No decision yet — waiting for first bar close
        </div>
      </div>
    );
  }

  const getOutcomeStatus = (outcome: string) => {
    if (outcome === 'TRADE') return 'good';
    if (outcome === 'HALT') return 'bad';
    return 'neutral';
  };

  return (
    <div className={cn('bg-[#111826] border border-[#22304A] rounded-xl p-6 space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-[#E7EEF9]">Current Decision</h3>
        <StatusBadge status={getOutcomeStatus(decision.outcome)}>
          {decision.outcome}
        </StatusBadge>
      </div>

      {/* EUC Score */}
      <div className="space-y-3">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-semibold text-[#E7EEF9] tabular-nums">
            {decision.euc.total.toFixed(2)}
          </span>
          <span className="text-sm text-[#7F93B2]">EUC Score</span>
        </div>

        <MetricBar
          label="Edge"
          value={decision.euc.edge}
          max={10}
          color="good"
        />
        <MetricBar
          label="Uncertainty"
          value={decision.euc.uncertainty}
          max={10}
          color="warn"
        />
        <MetricBar
          label="Cost"
          value={decision.euc.cost}
          max={10}
          color="bad"
        />
      </div>

      {/* Capital Tier & Risk Budget */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-xs text-[#7F93B2] mb-2">Capital Tier</div>
          <div className="text-lg font-semibold text-[#E7EEF9]">{decision.capital_tier}</div>
        </div>
        <div>
          <div className="text-xs text-[#7F93B2] mb-2">Risk Budget</div>
          <div className="text-lg font-semibold text-[#E7EEF9] tabular-nums">
            {((decision.risk_budget.today_consumed / decision.risk_budget.max_daily) * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Active Template */}
      {decision.active_template && (
        <div>
          <div className="text-xs text-[#7F93B2] mb-2">Active Template</div>
          <StatusBadge status="info">{decision.active_template}</StatusBadge>
        </div>
      )}

      {/* Proposed Order */}
      {decision.proposed_order && (
        <div className="space-y-3 p-4 bg-[#162033] rounded-lg border border-[#22304A]">
          <div className="text-xs text-[#7F93B2] mb-2">Proposed Order</div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-[#7F93B2]">Entry:</span>{' '}
              <span className="text-[#E7EEF9] font-mono tabular-nums">
                {decision.proposed_order.entry_price.toFixed(2)}
              </span>
            </div>
            <div>
              <span className="text-[#7F93B2]">Stop:</span>{' '}
              <span className="text-[#E7EEF9] font-mono tabular-nums">
                {decision.proposed_order.stop_price.toFixed(2)}
              </span>
            </div>
            <div>
              <span className="text-[#7F93B2]">Target:</span>{' '}
              <span className="text-[#E7EEF9] font-mono tabular-nums">
                {decision.proposed_order.target_price.toFixed(2)}
              </span>
            </div>
            <div>
              <span className="text-[#7F93B2]">Size:</span>{' '}
              <span className="text-[#E7EEF9] font-mono tabular-nums">
                {decision.proposed_order.position_size}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Why Not */}
      {decision.why_not && (
        <div className="space-y-3 p-4 bg-[#162033] rounded-lg border border-[#FFB020]">
          <div className="flex items-center gap-2">
            <div className="text-xs font-semibold text-[#FFB020]">WHY NOT?</div>
          </div>
          <div className="text-sm text-[#E7EEF9]">{decision.why_not.primary_blocker}</div>
          <div className="space-y-1">
            <div className="text-xs text-[#7F93B2]">Gate Failed:</div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-[#B8C7E0]">{decision.why_not.failed_gate.gate_name}</span>
              <div className="flex gap-2 font-mono tabular-nums text-xs">
                <span className="text-[#7F93B2]">
                  Required: {decision.why_not.failed_gate.threshold_required?.toFixed(2)}
                </span>
                <span className="text-[#FF5A5F]">
                  Current: {decision.why_not.failed_gate.current_value?.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
          <div className="text-xs text-[#B8C7E0] pt-2 border-t border-[#22304A]">
            {decision.why_not.what_would_change}
          </div>
        </div>
      )}

      {/* Counterfactual Toggles */}
      <div className="pt-4 border-t border-[#22304A]">
        <div className="text-xs text-[#7F93B2] mb-3">Counterfactual Simulation</div>
        <div className="space-y-2">
          <button className="w-full px-3 py-2 bg-[#162033] text-[#B8C7E0] border border-[#22304A] rounded text-xs text-left hover:border-[#B38BFF] transition-colors">
            If friction were optimistic → Would it trade?
          </button>
          <button className="w-full px-3 py-2 bg-[#162033] text-[#B8C7E0] border border-[#22304A] rounded text-xs text-left hover:border-[#B38BFF] transition-colors">
            If uncertainty reduced by 20% → Would it trade?
          </button>
        </div>
      </div>
    </div>
  );
}
