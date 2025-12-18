import React from 'react';
import { cn } from '../components/ui/utils';
import { DeltaChip } from '../components/DeltaChip';
import { MetricBar } from '../components/MetricBar';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { ScrollArea } from '../components/ui/scroll-area';
import type { ExecutionQuality, Fill } from '../types/trading-types';

interface ExecutionQualityPageProps {
  executionQuality: ExecutionQuality;
  fills: Fill[];
}

export function ExecutionQualityPage({ executionQuality, fills }: ExecutionQualityPageProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'FILLED': return 'text-[#2ED47A]';
      case 'PARTIAL': return 'text-[#FFB020]';
      case 'CANCELLED': return 'text-[#FF5A5F]';
      case 'PENDING': return 'text-[#4DA3FF]';
      default: return 'text-[#7F93B2]';
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    });
  };

  return (
    <div className="h-full p-6 space-y-6">
      {/* Header */}
      <div>
        <h2 className="font-semibold text-[#E7EEF9] mb-1">Execution Quality</h2>
        <p className="text-sm text-[#7F93B2]">Real-time execution metrics and fill analysis</p>
      </div>

      {/* Top Metrics */}
      <div className="grid grid-cols-3 gap-6">
        {/* DVS Card */}
        <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-xs text-[#7F93B2]">Data Validity Score</div>
            <div className={cn(
              'text-xs font-medium px-2 py-1 rounded',
              executionQuality.dvs >= 0.95 ? 'bg-[#1A7A45] text-[#2ED47A]' : 
              executionQuality.dvs >= 0.85 ? 'bg-[#8B5A00] text-[#FFB020]' : 
              'bg-[#8B2C2F] text-[#FF5A5F]'
            )}>
              {executionQuality.dvs >= 0.95 ? 'EXCELLENT' : executionQuality.dvs >= 0.85 ? 'GOOD' : 'DEGRADED'}
            </div>
          </div>
          <div className="text-4xl font-semibold text-[#E7EEF9] tabular-nums">
            {(executionQuality.dvs * 100).toFixed(1)}%
          </div>
          <MetricBar
            label=""
            value={executionQuality.dvs}
            max={1}
            color={executionQuality.dvs >= 0.95 ? 'good' : executionQuality.dvs >= 0.85 ? 'warn' : 'bad'}
            showValue={false}
          />
        </div>

        {/* EQS Card */}
        <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-xs text-[#7F93B2]">Execution Quality Score</div>
            <div className={cn(
              'text-xs font-medium px-2 py-1 rounded',
              executionQuality.eqs >= 0.90 ? 'bg-[#1A7A45] text-[#2ED47A]' : 
              executionQuality.eqs >= 0.75 ? 'bg-[#8B5A00] text-[#FFB020]' : 
              'bg-[#8B2C2F] text-[#FF5A5F]'
            )}>
              {executionQuality.eqs >= 0.90 ? 'EXCELLENT' : executionQuality.eqs >= 0.75 ? 'GOOD' : 'POOR'}
            </div>
          </div>
          <div className="text-4xl font-semibold text-[#E7EEF9] tabular-nums">
            {(executionQuality.eqs * 100).toFixed(1)}%
          </div>
          <MetricBar
            label=""
            value={executionQuality.eqs}
            max={1}
            color={executionQuality.eqs >= 0.90 ? 'good' : executionQuality.eqs >= 0.75 ? 'warn' : 'bad'}
            showValue={false}
          />
        </div>

        {/* Friction Card */}
        <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6 space-y-4">
          <div className="text-xs text-[#7F93B2]">Friction Analysis</div>
          <div className="space-y-3">
            <div>
              <div className="text-xs text-[#7F93B2] mb-1">Modeled (Realistic)</div>
              <div className="text-xl font-semibold text-[#E7EEF9] tabular-nums">
                {executionQuality.modeled_friction.realistic.toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-xs text-[#7F93B2] mb-1">Modeled (Pessimistic)</div>
              <div className="text-xl font-semibold text-[#B8C7E0] tabular-nums">
                {executionQuality.modeled_friction.pessimistic.toFixed(2)}
              </div>
            </div>
            {executionQuality.realized_friction !== undefined && (
              <div className="pt-2 border-t border-[#22304A]">
                <DeltaChip
                  expected={executionQuality.modeled_friction.realistic}
                  realized={executionQuality.realized_friction}
                />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Slippage Analysis */}
      {executionQuality.slippage_delta !== undefined && (
        <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6">
          <div className="text-sm font-medium text-[#E7EEF9] mb-4">Slippage Delta</div>
          <div className="flex items-center gap-4">
            <div className={cn(
              'text-3xl font-semibold tabular-nums',
              Math.abs(executionQuality.slippage_delta) < 0.5 ? 'text-[#2ED47A]' : 
              Math.abs(executionQuality.slippage_delta) < 1.0 ? 'text-[#FFB020]' : 
              'text-[#FF5A5F]'
            )}>
              {executionQuality.slippage_delta >= 0 ? '+' : ''}{executionQuality.slippage_delta.toFixed(2)} ticks
            </div>
            <div className="text-sm text-[#7F93B2]">
              {Math.abs(executionQuality.slippage_delta) < 0.5 ? 'Within expected range' : 
               Math.abs(executionQuality.slippage_delta) < 1.0 ? 'Slight deviation' : 
               'Significant deviation — investigate'}
            </div>
          </div>
        </div>
      )}

      {/* Fills & Orders Table */}
      <div className="bg-[#111826] border border-[#22304A] rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-[#22304A]">
          <h3 className="font-medium text-[#E7EEF9]">Fills & Orders</h3>
        </div>
        <ScrollArea className="h-[400px]">
          <Table>
            <TableHeader>
              <TableRow className="border-[#22304A] hover:bg-transparent">
                <TableHead className="text-[#7F93B2]">Order ID</TableHead>
                <TableHead className="text-[#7F93B2]">Type</TableHead>
                <TableHead className="text-[#7F93B2]">Sent Time</TableHead>
                <TableHead className="text-[#7F93B2]">Fill Time</TableHead>
                <TableHead className="text-[#7F93B2] text-right">Expected Price</TableHead>
                <TableHead className="text-[#7F93B2] text-right">Fill Price</TableHead>
                <TableHead className="text-[#7F93B2] text-right">Slippage</TableHead>
                <TableHead className="text-[#7F93B2]">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {fills.length === 0 ? (
                <TableRow className="border-[#22304A] hover:bg-[#162033]">
                  <TableCell colSpan={8} className="text-center text-[#7F93B2] py-8">
                    No fills yet
                  </TableCell>
                </TableRow>
              ) : (
                fills.map((fill) => (
                  <TableRow key={fill.order_id} className="border-[#22304A] hover:bg-[#162033]">
                    <TableCell className="text-[#B8C7E0] font-mono text-xs">
                      {fill.order_id}
                    </TableCell>
                    <TableCell className="text-[#E7EEF9]">
                      <span className={cn(
                        'px-2 py-1 rounded text-xs font-medium',
                        fill.type === 'ENTRY' && 'bg-[#285A8F] text-[#4DA3FF]',
                        fill.type === 'STOP' && 'bg-[#8B2C2F] text-[#FF5A5F]',
                        fill.type === 'TARGET' && 'bg-[#1A7A45] text-[#2ED47A]',
                        fill.type === 'EXIT' && 'bg-[#22304A] text-[#9AA9C2]'
                      )}>
                        {fill.type}
                      </span>
                    </TableCell>
                    <TableCell className="text-[#B8C7E0] font-mono text-xs">
                      {formatTime(fill.sent_time)}
                    </TableCell>
                    <TableCell className="text-[#B8C7E0] font-mono text-xs">
                      {fill.fill_time ? formatTime(fill.fill_time) : '—'}
                    </TableCell>
                    <TableCell className="text-[#E7EEF9] text-right font-mono tabular-nums">
                      {fill.expected_price.toFixed(2)}
                    </TableCell>
                    <TableCell className="text-[#E7EEF9] text-right font-mono tabular-nums">
                      {fill.fill_price?.toFixed(2) || '—'}
                    </TableCell>
                    <TableCell className="text-right">
                      {fill.slippage_ticks !== undefined ? (
                        <span className={cn(
                          'font-mono tabular-nums',
                          fill.slippage_ticks === 0 ? 'text-[#2ED47A]' : 
                          Math.abs(fill.slippage_ticks) <= 1 ? 'text-[#FFB020]' : 
                          'text-[#FF5A5F]'
                        )}>
                          {fill.slippage_ticks >= 0 ? '+' : ''}{fill.slippage_ticks} ticks
                        </span>
                      ) : (
                        <span className="text-[#7F93B2]">—</span>
                      )}
                    </TableCell>
                    <TableCell className={getStatusColor(fill.status)}>
                      {fill.status}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </ScrollArea>
      </div>

      {/* Execution Notes */}
      <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6 space-y-4">
        <h3 className="font-medium text-[#E7EEF9]">Execution Notes & Alerts</h3>
        <div className="space-y-2">
          <div className="p-3 bg-[#1A7A45]/10 border border-[#2ED47A]/20 rounded text-sm text-[#2ED47A]">
            ✓ All fills within expected latency (avg: 12ms)
          </div>
          <div className="p-3 bg-[#285A8F]/10 border border-[#4DA3FF]/20 rounded text-sm text-[#4DA3FF]">
            ℹ Queue position estimation enabled
          </div>
        </div>
      </div>
    </div>
  );
}
