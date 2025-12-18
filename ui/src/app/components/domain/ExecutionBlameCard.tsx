/**
 * ExecutionBlameCard - Separates strategy quality from execution quality
 * Critical for not blaming the model for poor fills
 */

import { Card } from '../primitives/Card';
import { NumericValue } from '../primitives/NumericValue';

interface ExecutionBlame {
  tradeId: string;
  expectedFillPrice: number;
  realizedFillPrice: number;
  expectedSlippage: number;
  realizedSlippage: number;
  strategyQuality: number; // -1 to 1
  executionQuality: number; // -1 to 1
  marketNoise: number; // 0 to 1
  fillType: 'FULL' | 'PARTIAL' | 'MISSED';
}

interface ExecutionBlameCardProps {
  execution: ExecutionBlame;
  className?: string;
}

export function ExecutionBlameCard({ execution, className = '' }: ExecutionBlameCardProps) {
  const slippageDelta = execution.realizedSlippage - execution.expectedSlippage;
  const isSlippageGood = slippageDelta < 0; // Negative slippage is good (better fill)

  return (
    <Card className={className}>
      <h4 className="text-sm font-semibold text-[var(--text-0)] uppercase tracking-wide mb-3">
        Execution Analysis
      </h4>

      {/* Fill Comparison */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="p-3 bg-[var(--bg-2)] rounded">
          <div className="text-xs text-[var(--text-2)] mb-1">Expected Fill</div>
          <div className="font-mono text-[var(--text-0)]">
            <NumericValue value={execution.expectedFillPrice} decimals={2} />
          </div>
          <div className="text-xs text-[var(--text-2)] mt-1">
            Slippage: <NumericValue value={execution.expectedSlippage} decimals={4} />
          </div>
        </div>
        <div className="p-3 bg-[var(--bg-2)] rounded">
          <div className="text-xs text-[var(--text-2)] mb-1">Realized Fill</div>
          <div className="font-mono text-[var(--text-0)]">
            <NumericValue value={execution.realizedFillPrice} decimals={2} />
          </div>
          <div className="text-xs mt-1">
            Slippage: <NumericValue value={execution.realizedSlippage} decimals={4} delta={true} />
          </div>
        </div>
      </div>

      {/* Slippage Delta */}
      <div className="mb-4 p-3 rounded border border-[var(--stroke-0)]">
        <div className="flex items-center justify-between">
          <span className="text-xs text-[var(--text-2)] uppercase tracking-wide">
            Slippage Delta
          </span>
          <span className={`font-mono text-sm ${isSlippageGood ? 'text-[var(--good)]' : 'text-[var(--bad)]'}`}>
            <NumericValue value={slippageDelta} decimals={4} delta={true} />
            {isSlippageGood ? ' (Better)' : ' (Worse)'}
          </span>
        </div>
      </div>

      {/* Blame Separation */}
      <div className="space-y-3">
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-[var(--text-2)] uppercase tracking-wide">
              Strategy Quality
            </span>
            <span className={`font-mono text-sm ${
              execution.strategyQuality > 0 ? 'text-[var(--good)]' : 'text-[var(--bad)]'
            }`}>
              <NumericValue value={execution.strategyQuality} decimals={2} delta={true} />
            </span>
          </div>
          <div className="h-2 bg-[var(--bg-3)] rounded overflow-hidden">
            <div
              className={`h-full ${execution.strategyQuality > 0 ? 'bg-[var(--good)]' : 'bg-[var(--bad)]'}`}
              style={{ width: `${Math.abs(execution.strategyQuality) * 50}%` }}
            />
          </div>
          <div className="text-xs text-[var(--text-2)] mt-1">
            {execution.strategyQuality > 0 ? 'Good trade idea' : 'Poor trade idea'}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-[var(--text-2)] uppercase tracking-wide">
              Execution Quality
            </span>
            <span className={`font-mono text-sm ${
              execution.executionQuality > 0 ? 'text-[var(--good)]' : 'text-[var(--bad)]'
            }`}>
              <NumericValue value={execution.executionQuality} decimals={2} delta={true} />
            </span>
          </div>
          <div className="h-2 bg-[var(--bg-3)] rounded overflow-hidden">
            <div
              className={`h-full ${execution.executionQuality > 0 ? 'bg-[var(--good)]' : 'bg-[var(--bad)]'}`}
              style={{ width: `${Math.abs(execution.executionQuality) * 50}%` }}
            />
          </div>
          <div className="text-xs text-[var(--text-2)] mt-1">
            {execution.executionQuality > 0 ? 'Good execution' : 'Poor execution'}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-[var(--text-2)] uppercase tracking-wide">
              Market Noise
            </span>
            <span className="font-mono text-sm text-[var(--text-1)]">
              <NumericValue value={execution.marketNoise} format="percentage" decimals={0} />
            </span>
          </div>
          <div className="h-2 bg-[var(--bg-3)] rounded overflow-hidden">
            <div
              className="h-full bg-[var(--neutral)]"
              style={{ width: `${execution.marketNoise * 100}%` }}
            />
          </div>
          <div className="text-xs text-[var(--text-2)] mt-1">
            Unavoidable market randomness
          </div>
        </div>
      </div>

      {/* Fill Type */}
      <div className="mt-4 pt-4 border-t border-[var(--stroke-0)]">
        <div className="flex items-center justify-between">
          <span className="text-xs text-[var(--text-2)] uppercase tracking-wide">Fill Type</span>
          <span className={`text-sm font-medium ${
            execution.fillType === 'FULL' ? 'text-[var(--good)]' :
            execution.fillType === 'PARTIAL' ? 'text-[var(--warn)]' :
            'text-[var(--bad)]'
          }`}>
            {execution.fillType}
          </span>
        </div>
      </div>
    </Card>
  );
}
