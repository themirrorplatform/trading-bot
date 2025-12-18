import React from 'react';
import { cn } from './ui/utils';
import { MetricBar } from './MetricBar';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { BeliefState, Constraint } from '../types/trading-types';

interface BeliefStateInspectorProps {
  constraint: Constraint | null;
  beliefState: BeliefState | null;
  className?: string;
}

export function BeliefStateInspector({ constraint, beliefState, className }: BeliefStateInspectorProps) {
  if (!constraint || !beliefState) {
    return (
      <div className={cn('bg-[#111826] border border-[#22304A] rounded-xl p-6', className)}>
        <div className="text-center text-[#7F93B2] py-8">
          Select a constraint to view belief state details
        </div>
      </div>
    );
  }

  return (
    <div className={cn('bg-[#111826] border border-[#22304A] rounded-xl p-6 space-y-6', className)}>
      {/* Header */}
      <div>
        <h3 className="font-semibold text-[#E7EEF9]">{constraint.constraint_name}</h3>
        <div className="text-xs text-[#7F93B2] mt-1">
          Last Updated: {new Date(beliefState.last_updated).toLocaleTimeString()}
        </div>
      </div>

      {/* Probability Trend */}
      <div>
        <div className="text-xs text-[#7F93B2] mb-3">Probability Trend</div>
        <div className="flex items-baseline gap-3">
          <span className="text-3xl font-semibold text-[#E7EEF9] tabular-nums">
            {(beliefState.probability * 100).toFixed(1)}%
          </span>
          <div className="flex items-center gap-1 text-sm">
            {beliefState.probability > 0.5 ? (
              <>
                <TrendingUp className="w-4 h-4 text-[#2ED47A]" />
                <span className="text-[#2ED47A]">Strong</span>
              </>
            ) : beliefState.probability > 0.3 ? (
              <>
                <Minus className="w-4 h-4 text-[#FFB020]" />
                <span className="text-[#FFB020]">Moderate</span>
              </>
            ) : (
              <>
                <TrendingDown className="w-4 h-4 text-[#FF5A5F]" />
                <span className="text-[#FF5A5F]">Weak</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="space-y-3">
        <MetricBar
          label="Confidence"
          value={beliefState.confidence}
          max={1}
          color="good"
        />
        <MetricBar
          label="Stability (EWMA)"
          value={beliefState.stability_ewma}
          max={1}
          color="info"
        />
        <MetricBar
          label="Decay State"
          value={constraint.decay_state}
          max={1}
          color="accent"
        />
      </div>

      {/* Dominance Rank */}
      <div className="bg-[#162033] border border-[#22304A] rounded-lg p-4">
        <div className="text-xs text-[#7F93B2] mb-2">Dominance Rank</div>
        <div className="flex items-center gap-2">
          <div className="text-2xl font-semibold text-[#E7EEF9]">
            #{constraint.dominance_rank}
          </div>
          <div className="text-sm text-[#B8C7E0]">
            {constraint.dominance_rank === 1 ? '(Primary Driver)' : '(Contributing)'}
          </div>
        </div>
      </div>

      {/* Applicability Gates */}
      <div>
        <div className="text-xs text-[#7F93B2] mb-2">Applicability Gates</div>
        <div className="grid grid-cols-3 gap-2">
          {Object.entries(constraint.applicability_gates).map(([gate, active]) => (
            <div
              key={gate}
              className={cn(
                'px-3 py-2 rounded text-xs text-center',
                active
                  ? 'bg-[#1A7A45] text-[#2ED47A]'
                  : 'bg-[#22304A] text-[#7F93B2]'
              )}
            >
              {gate.toUpperCase()}
            </div>
          ))}
        </div>
      </div>

      {/* Evidence For */}
      {beliefState.evidence_for.length > 0 && (
        <div>
          <div className="text-xs text-[#7F93B2] mb-2">Evidence For</div>
          <div className="space-y-1">
            {beliefState.evidence_for.map((evidence, i) => (
              <div
                key={i}
                className="flex items-start gap-2 text-sm text-[#2ED47A] bg-[#1A7A45]/10 p-2 rounded"
              >
                <span className="text-[#2ED47A] mt-0.5">✓</span>
                <span className="flex-1">{evidence}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evidence Against */}
      {beliefState.evidence_against.length > 0 && (
        <div>
          <div className="text-xs text-[#7F93B2] mb-2">Evidence Against</div>
          <div className="space-y-1">
            {beliefState.evidence_against.map((evidence, i) => (
              <div
                key={i}
                className="flex items-start gap-2 text-sm text-[#FF5A5F] bg-[#8B2C2F]/10 p-2 rounded"
              >
                <span className="text-[#FF5A5F] mt-0.5">✗</span>
                <span className="flex-1">{evidence}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evidence Unknown */}
      {beliefState.evidence_unknown.length > 0 && (
        <div>
          <div className="text-xs text-[#7F93B2] mb-2">Unknown / Uncertain</div>
          <div className="space-y-1">
            {beliefState.evidence_unknown.map((evidence, i) => (
              <div
                key={i}
                className="flex items-start gap-2 text-sm text-[#FFB020] bg-[#8B5A00]/10 p-2 rounded"
              >
                <span className="text-[#FFB020] mt-0.5">?</span>
                <span className="flex-1">{evidence}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* What Would Flip */}
      <div className="pt-4 border-t border-[#22304A]">
        <div className="text-xs text-[#7F93B2] mb-2">What Would Flip This Belief?</div>
        <div className="text-sm text-[#B8C7E0] bg-[#162033] p-3 rounded">
          <div>• Signal S5 reliability increase to &gt; 0.85</div>
          <div>• Session volume above 2000</div>
          <div>• Regime stability &gt; 0.90</div>
        </div>
      </div>
    </div>
  );
}
