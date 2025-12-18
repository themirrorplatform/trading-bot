/**
 * BeliefStatePanel - Shows active beliefs at decision time
 * Critical for understanding what the bot believed and why
 */

import { Card } from '../primitives/Card';
import { NumericValue } from '../primitives/NumericValue';
import { StatusChip } from '../primitives/StatusChip';

interface Belief {
  name: string;
  probability: number;
  stability: number; // EWMA stability
  decayState: 'ACTIVE' | 'DECAYING' | 'STALE';
  applicabilityGates: Array<{
    name: string;
    status: 'PASS' | 'FAIL' | 'NA';
  }>;
  evidenceFor: number;
  evidenceAgainst: number;
  evidenceUnknown: number;
  lastUpdate: string;
}

interface BeliefStatePanelProps {
  beliefs: Belief[];
  highlightDominant?: boolean;
  className?: string;
}

export function BeliefStatePanel({ beliefs, highlightDominant = false, className = '' }: BeliefStatePanelProps) {
  // Sort by probability to identify dominant beliefs
  const sortedBeliefs = [...beliefs].sort((a, b) => b.probability - a.probability);
  const dominantThreshold = 0.7;

  const getDecayColor = (state: string) => {
    switch (state) {
      case 'ACTIVE': return 'text-[var(--good)]';
      case 'DECAYING': return 'text-[var(--warn)]';
      case 'STALE': return 'text-[var(--bad)]';
      default: return 'text-[var(--text-2)]';
    }
  };

  return (
    <Card className={className}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[var(--text-0)] uppercase tracking-wide">
          Active Beliefs
        </h3>
        <span className="text-xs text-[var(--text-2)]">
          {beliefs.length} belief{beliefs.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="space-y-3">
        {sortedBeliefs.map((belief, index) => {
          const isDominant = belief.probability >= dominantThreshold;
          const allGatesPass = belief.applicabilityGates.every(g => g.status === 'PASS');

          return (
            <div
              key={index}
              className={`p-3 rounded border ${
                isDominant && highlightDominant
                  ? 'border-[var(--accent)] bg-[var(--accent-bg)]'
                  : 'border-[var(--stroke-0)] bg-[var(--bg-2)]'
              }`}
            >
              {/* Belief Header */}
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="text-sm font-medium text-[var(--text-0)] mb-1">
                    {belief.name}
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-[var(--text-2)]">
                      Probability: <span className="font-mono text-[var(--text-0)]">
                        <NumericValue value={belief.probability} format="percentage" decimals={1} />
                      </span>
                    </span>
                    <span className="text-[var(--text-2)]">
                      Stability: <span className="font-mono text-[var(--text-0)]">
                        <NumericValue value={belief.stability} decimals={3} />
                      </span>
                    </span>
                  </div>
                </div>
                <span className={`text-xs font-medium uppercase ${getDecayColor(belief.decayState)}`}>
                  {belief.decayState}
                </span>
              </div>

              {/* Evidence Distribution */}
              <div className="mb-2">
                <div className="text-xs text-[var(--text-2)] mb-1">Evidence Distribution</div>
                <div className="flex h-2 rounded overflow-hidden">
                  <div
                    className="bg-[var(--good)]"
                    style={{ width: `${belief.evidenceFor * 100}%` }}
                    title={`For: ${(belief.evidenceFor * 100).toFixed(0)}%`}
                  />
                  <div
                    className="bg-[var(--bad)]"
                    style={{ width: `${belief.evidenceAgainst * 100}%` }}
                    title={`Against: ${(belief.evidenceAgainst * 100).toFixed(0)}%`}
                  />
                  <div
                    className="bg-[var(--neutral)]"
                    style={{ width: `${belief.evidenceUnknown * 100}%` }}
                    title={`Unknown: ${(belief.evidenceUnknown * 100).toFixed(0)}%`}
                  />
                </div>
                <div className="flex items-center justify-between mt-1 text-xs">
                  <span className="text-[var(--good)]">
                    For: <NumericValue value={belief.evidenceFor} format="percentage" decimals={0} />
                  </span>
                  <span className="text-[var(--bad)]">
                    Against: <NumericValue value={belief.evidenceAgainst} format="percentage" decimals={0} />
                  </span>
                  <span className="text-[var(--neutral)]">
                    Unknown: <NumericValue value={belief.evidenceUnknown} format="percentage" decimals={0} />
                  </span>
                </div>
              </div>

              {/* Applicability Gates */}
              {belief.applicabilityGates.length > 0 && (
                <div>
                  <div className="text-xs text-[var(--text-2)] mb-1">Applicability Gates</div>
                  <div className="flex flex-wrap gap-1">
                    {belief.applicabilityGates.map((gate, i) => (
                      <div key={i} className="flex items-center gap-1">
                        <StatusChip status={gate.status} />
                        <span className="text-xs text-[var(--text-1)]">{gate.name}</span>
                      </div>
                    ))}
                  </div>
                  {!allGatesPass && (
                    <div className="mt-1 text-xs text-[var(--warn)]">
                      ⚠ Belief applicable but some gates not met
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
