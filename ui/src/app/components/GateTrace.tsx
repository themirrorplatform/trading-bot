import React from 'react';
import { cn } from './ui/utils';
import { CheckCircle2, XCircle, Minus, AlertCircle } from 'lucide-react';
import { ReasonCodeChip } from './ReasonCodeChip';
import type { GateResult } from '../types/trading-types';

interface GateTraceProps {
  gates: GateResult[];
  className?: string;
}

export function GateTrace({ gates, className }: GateTraceProps) {
  const getGateIcon = (status: string) => {
    switch (status) {
      case 'PASS':
        return <CheckCircle2 className="w-4 h-4 text-[#2ED47A]" />;
      case 'FAIL':
        return <XCircle className="w-4 h-4 text-[#FF5A5F]" />;
      case 'NOT_APPLICABLE':
        return <Minus className="w-4 h-4 text-[#7F93B2]" />;
      case 'ERROR':
        return <AlertCircle className="w-4 h-4 text-[#FFB020]" />;
      default:
        return <Minus className="w-4 h-4 text-[#7F93B2]" />;
    }
  };

  return (
    <div className={cn('space-y-2', className)}>
      {gates.map((gate, index) => (
        <div
          key={gate.gate_id}
          className={cn(
            'p-4 rounded-lg border transition-colors',
            gate.status === 'PASS' && 'bg-[#1A7A45]/10 border-[#2ED47A]/20',
            gate.status === 'FAIL' && 'bg-[#8B2C2F]/10 border-[#FF5A5F]/20',
            gate.status === 'NOT_APPLICABLE' && 'bg-[#162033] border-[#22304A]',
            gate.status === 'ERROR' && 'bg-[#8B5A00]/10 border-[#FFB020]/20'
          )}
        >
          <div className="flex items-start gap-3">
            {getGateIcon(gate.status)}
            
            <div className="flex-1 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-[#E7EEF9]">
                  {gate.gate_name}
                </span>
                <span className={cn(
                  'text-xs font-medium px-2 py-0.5 rounded',
                  gate.status === 'PASS' && 'bg-[#1A7A45] text-[#2ED47A]',
                  gate.status === 'FAIL' && 'bg-[#8B2C2F] text-[#FF5A5F]',
                  gate.status === 'NOT_APPLICABLE' && 'bg-[#22304A] text-[#7F93B2]',
                  gate.status === 'ERROR' && 'bg-[#8B5A00] text-[#FFB020]'
                )}>
                  {gate.status}
                </span>
              </div>

              {(gate.threshold_required !== undefined || gate.current_value !== undefined) && (
                <div className="flex items-center gap-4 text-xs font-mono tabular-nums">
                  {gate.threshold_required !== undefined && (
                    <span className="text-[#7F93B2]">
                      Required: <span className="text-[#B8C7E0]">{gate.threshold_required.toFixed(2)}</span>
                    </span>
                  )}
                  {gate.current_value !== undefined && (
                    <span className="text-[#7F93B2]">
                      Current: <span className={cn(
                        gate.status === 'PASS' ? 'text-[#2ED47A]' : 'text-[#FF5A5F]'
                      )}>{gate.current_value.toFixed(2)}</span>
                    </span>
                  )}
                </div>
              )}

              {gate.reason_codes.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {gate.reason_codes.map((code, i) => (
                    <ReasonCodeChip key={i} code={code} />
                  ))}
                </div>
              )}

              {gate.evidence.length > 0 && (
                <div className="space-y-1 pt-2 border-t border-[#22304A]">
                  {gate.evidence.map((ev, i) => (
                    <div key={i} className="text-xs text-[#B8C7E0]">• {ev}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
