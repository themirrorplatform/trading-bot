import React from 'react';
import { cn } from './ui/utils';
import { StatusBadge } from './StatusBadge';
import { MetricBar } from './MetricBar';
import { DeltaChip } from './DeltaChip';
import type { AttributionV2 } from '../types/trading-types';

interface AttributionCardProps {
  attribution: AttributionV2;
  className?: string;
}

export function AttributionCard({ attribution, className }: AttributionCardProps) {
  const getClassificationColor = (classification: string) => {
    if (classification.includes('GOOD')) return 'good';
    if (classification.includes('LUCKY')) return 'warn';
    if (classification.includes('BAD')) return 'bad';
    return 'neutral';
  };

  const getClassificationLabel = (classification: string) => {
    return classification.replace(/_/g, ' ');
  };

  return (
    <div className={cn('bg-[#111826] border border-[#22304A] rounded-xl p-6 space-y-6', className)}>
      {/* Classification */}
      <div>
        <div className="text-xs text-[#7F93B2] mb-2">Attribution Classification</div>
        <StatusBadge status={getClassificationColor(attribution.classification)} className="text-sm">
          {getClassificationLabel(attribution.classification)}
        </StatusBadge>
      </div>

      {/* Learning Weight */}
      <div>
        <div className="text-xs text-[#7F93B2] mb-2">Learning Weight Applied</div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-semibold text-[#E7EEF9] tabular-nums">
            {(attribution.learning_weight * 100).toFixed(0)}%
          </span>
          <span className="text-sm text-[#7F93B2]">
            {attribution.learning_weight > 0.8 ? 'High confidence' : 
             attribution.learning_weight > 0.5 ? 'Moderate confidence' : 
             'Low confidence — likely noise'}
          </span>
        </div>
        <div className="h-2 bg-[#162033] rounded-full overflow-hidden mt-2">
          <div
            className={cn(
              'h-full',
              attribution.learning_weight > 0.8 ? 'bg-[#2ED47A]' : 
              attribution.learning_weight > 0.5 ? 'bg-[#FFB020]' : 
              'bg-[#FF5A5F]'
            )}
            style={{ width: `${attribution.learning_weight * 100}%` }}
          />
        </div>
      </div>

      {/* Contribution Breakdown */}
      <div className="space-y-3">
        <div className="text-xs text-[#7F93B2]">Contribution Breakdown</div>
        <MetricBar
          label="Edge"
          value={attribution.edge_contribution}
          max={100}
          color="good"
        />
        <MetricBar
          label="Luck"
          value={attribution.luck_contribution}
          max={100}
          color="warn"
        />
        <MetricBar
          label="Execution"
          value={attribution.execution_contribution}
          max={100}
          color="info"
        />
      </div>

      {/* Expected vs Realized */}
      <div className="pt-4 border-t border-[#22304A] space-y-3">
        <div className="text-xs text-[#7F93B2]">Expected vs Realized Outcome</div>
        
        {/* Expected Range */}
        <div className="bg-[#162033] rounded-lg p-4">
          <div className="text-xs text-[#7F93B2] mb-2">Expected Range</div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-[#B8C7E0]">
              ${attribution.expected_outcome.range[0].toFixed(2)}
            </span>
            <span className="text-[#E7EEF9] font-semibold">
              Mean: ${attribution.expected_outcome.mean.toFixed(2)}
            </span>
            <span className="text-[#B8C7E0]">
              ${attribution.expected_outcome.range[1].toFixed(2)}
            </span>
          </div>
          
          {/* Visual Range */}
          <div className="mt-3 relative h-8 bg-[#111826] rounded-lg overflow-hidden">
            <div 
              className="absolute top-0 bottom-0 bg-[#B38BFF]/20 border-l-2 border-r-2 border-[#B38BFF]"
              style={{
                left: '20%',
                right: '20%',
              }}
            />
            <div
              className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-[#B38BFF]"
              style={{ left: '50%', transform: 'translate(-50%, -50%)' }}
            />
          </div>
        </div>

        {/* Realized */}
        <div>
          <DeltaChip
            expected={attribution.expected_outcome.mean}
            realized={attribution.realized_outcome}
            unit="$"
          />
        </div>

        {/* Deception Detector */}
        {attribution.classification.includes('LUCKY') && (
          <div className="bg-[#8B5A00]/10 border border-[#FFB020]/20 rounded-lg p-3 text-sm text-[#FFB020]">
            ⚠ Deception Risk: Model predicted strong edge, but attribution suggests luck.
            Learning weight reduced to prevent overfitting.
          </div>
        )}
      </div>
    </div>
  );
}
