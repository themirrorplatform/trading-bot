import React, { useState } from 'react';
import { cn } from '../components/ui/utils';
import { ConstraintSignalMatrix } from '../components/ConstraintSignalMatrix';
import { BeliefStateInspector } from '../components/BeliefStateInspector';
import { StatusBadge } from '../components/StatusBadge';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { ScrollArea } from '../components/ui/scroll-area';
import type { Constraint, BeliefState, Signal } from '../types/trading-types';

interface BeliefsConstraintsProps {
  constraints: Constraint[];
  beliefStates: BeliefState[];
  signals: Signal[];
}

export function BeliefsConstraints({ constraints, beliefStates, signals }: BeliefsConstraintsProps) {
  const [selectedConstraint, setSelectedConstraint] = useState<Constraint | null>(null);
  const [sortBy, setSortBy] = useState<'dominance' | 'probability' | 'instability'>('dominance');
  const [showBiasSurface, setShowBiasSurface] = useState(false);

  const sortedConstraints = [...constraints].sort((a, b) => {
    switch (sortBy) {
      case 'dominance':
        return a.dominance_rank - b.dominance_rank;
      case 'probability':
        return b.probability - a.probability;
      case 'instability':
        return a.stability - b.stability;
      default:
        return 0;
    }
  });

  const selectedBeliefState = selectedConstraint
    ? beliefStates.find((bs) => bs.constraint_id === selectedConstraint.constraint_id) || null
    : null;

  const getBiasLevel = (constraint: Constraint) => {
    // Over-dominant: rank 1-2 and high probability
    if (constraint.dominance_rank <= 2 && constraint.probability > 0.7) {
      return { level: 'Over-Dominant', color: 'warn' };
    }
    // Conflicting: high probability but low stability
    if (constraint.probability > 0.6 && constraint.stability < 0.7) {
      return { level: 'Conflicting', color: 'bad' };
    }
    // Under-observed: low probability and low stability
    if (constraint.probability < 0.4 && constraint.stability < 0.6) {
      return { level: 'Under-Observed', color: 'neutral' };
    }
    return null;
  };

  return (
    <div className="h-full p-6 grid grid-cols-12 gap-6">
      {/* Left: Constraints List */}
      <div className="col-span-3 space-y-4">
        <div>
          <h2 className="font-semibold text-[#E7EEF9] mb-1">Constraints</h2>
          <p className="text-sm text-[#7F93B2]">{constraints.length} active</p>
        </div>

        {/* Sort Controls */}
        <div className="space-y-2">
          <Label className="text-xs text-[#7F93B2]">Sort By</Label>
          <div className="flex gap-2">
            {['dominance', 'probability', 'instability'].map((sort) => (
              <button
                key={sort}
                onClick={() => setSortBy(sort as any)}
                className={cn(
                  'px-3 py-1.5 rounded text-xs transition-colors',
                  sortBy === sort
                    ? 'bg-[#B38BFF] text-[#0B0F14]'
                    : 'bg-[#162033] text-[#B8C7E0] border border-[#22304A] hover:border-[#B38BFF]'
                )}
              >
                {sort.charAt(0).toUpperCase() + sort.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Bias Surface Toggle */}
        <div className="flex items-center gap-2 p-3 bg-[#162033] rounded-lg border border-[#22304A]">
          <Switch
            checked={showBiasSurface}
            onCheckedChange={setShowBiasSurface}
            id="bias-surface"
          />
          <Label htmlFor="bias-surface" className="text-xs text-[#E7EEF9] cursor-pointer">
            Show Bias Surface
          </Label>
        </div>

        {/* Constraints List */}
        <ScrollArea className="h-[calc(100vh-340px)]">
          <div className="space-y-2">
            {sortedConstraints.map((constraint) => {
              const biasInfo = getBiasLevel(constraint);
              const isSelected = selectedConstraint?.constraint_id === constraint.constraint_id;

              return (
                <div
                  key={constraint.constraint_id}
                  onClick={() => setSelectedConstraint(constraint)}
                  className={cn(
                    'p-3 rounded-lg border cursor-pointer transition-all',
                    isSelected
                      ? 'bg-[#162033] border-[#B38BFF]'
                      : 'bg-[#111826] border-[#22304A] hover:border-[#B38BFF]'
                  )}
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-[#E7EEF9] font-mono truncate">
                          {constraint.constraint_name}
                        </div>
                        <div className="text-xs text-[#7F93B2] mt-1">
                          Rank #{constraint.dominance_rank}
                        </div>
                      </div>
                      {showBiasSurface && biasInfo && (
                        <StatusBadge status={biasInfo.color as any} className="text-[10px]">
                          {biasInfo.level}
                        </StatusBadge>
                      )}
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-[#7F93B2]">Probability</span>
                        <span className="text-[#E7EEF9] tabular-nums">
                          {(constraint.probability * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="h-1 bg-[#162033] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#B38BFF]"
                          style={{ width: `${constraint.probability * 100}%` }}
                        />
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-xs">
                      <span className="text-[#7F93B2]">Stability</span>
                      <span className="text-[#E7EEF9] tabular-nums">
                        {(constraint.stability * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </div>

      {/* Center: Constraint-Signal Matrix */}
      <div className="col-span-5 space-y-4">
        <div>
          <h2 className="font-semibold text-[#E7EEF9] mb-1">Constraint-Signal Matrix</h2>
          <p className="text-sm text-[#7F93B2]">Contribution weights</p>
        </div>

        <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6">
          <ScrollArea className="h-[calc(100vh-220px)]">
            <ConstraintSignalMatrix
              constraints={sortedConstraints}
              signals={signals}
              onCellClick={(constraint, signal, weight) => {
                console.log('Cell clicked:', constraint.constraint_name, signal.signal_code, weight);
              }}
            />
          </ScrollArea>
        </div>
      </div>

      {/* Right: Belief State Inspector */}
      <div className="col-span-4 space-y-4">
        <div>
          <h2 className="font-semibold text-[#E7EEF9] mb-1">Belief State</h2>
          <p className="text-sm text-[#7F93B2]">
            {selectedConstraint ? 'Details' : 'Select a constraint'}
          </p>
        </div>

        <ScrollArea className="h-[calc(100vh-180px)]">
          <BeliefStateInspector
            constraint={selectedConstraint}
            beliefState={selectedBeliefState}
          />
        </ScrollArea>
      </div>
    </div>
  );
}
