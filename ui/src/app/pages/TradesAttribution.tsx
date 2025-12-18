import React, { useState } from 'react';
import { cn } from '../components/ui/utils';
import { AttributionCard } from '../components/AttributionCard';
import { ScrollArea } from '../components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { TrendingUp, TrendingDown } from 'lucide-react';
import type { Trade } from '../types/trading-types';

interface TradesAttributionProps {
  trades: Trade[];
}

export function TradesAttribution({ trades }: TradesAttributionProps) {
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(trades[0] || null);
  const [filterDay, setFilterDay] = useState('all');
  const [filterTemplate, setFilterTemplate] = useState('all');
  const [filterOutcome, setFilterOutcome] = useState('all');
  const [filterAttribution, setFilterAttribution] = useState('all');

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', { 
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  };

  const getDuration = (entryTime: string, exitTime?: string) => {
    if (!exitTime) return 'In Progress';
    const entry = new Date(entryTime);
    const exit = new Date(exitTime);
    const durationMs = exit.getTime() - entry.getTime();
    const minutes = Math.floor(durationMs / 60000);
    const seconds = Math.floor((durationMs % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  };

  return (
    <div className="h-full p-6 grid grid-cols-12 gap-6">
      {/* Left: Trades List */}
      <div className="col-span-4 space-y-4">
        <div>
          <h2 className="font-semibold text-[#E7EEF9] mb-1">Trades</h2>
          <p className="text-sm text-[#7F93B2]">{trades.length} total</p>
        </div>

        {/* Filters */}
        <div className="grid grid-cols-2 gap-3">
          <Select value={filterDay} onValueChange={setFilterDay}>
            <SelectTrigger className="bg-[#111826] border-[#22304A] text-[#E7EEF9]">
              <SelectValue placeholder="Day" />
            </SelectTrigger>
            <SelectContent className="bg-[#111826] border-[#22304A]">
              <SelectItem value="all">All Days</SelectItem>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="yesterday">Yesterday</SelectItem>
            </SelectContent>
          </Select>

          <Select value={filterTemplate} onValueChange={setFilterTemplate}>
            <SelectTrigger className="bg-[#111826] border-[#22304A] text-[#E7EEF9]">
              <SelectValue placeholder="Template" />
            </SelectTrigger>
            <SelectContent className="bg-[#111826] border-[#22304A]">
              <SelectItem value="all">All Templates</SelectItem>
              <SelectItem value="K1">K1</SelectItem>
              <SelectItem value="K2">K2</SelectItem>
              <SelectItem value="K3">K3</SelectItem>
              <SelectItem value="K4">K4</SelectItem>
            </SelectContent>
          </Select>

          <Select value={filterOutcome} onValueChange={setFilterOutcome}>
            <SelectTrigger className="bg-[#111826] border-[#22304A] text-[#E7EEF9]">
              <SelectValue placeholder="Outcome" />
            </SelectTrigger>
            <SelectContent className="bg-[#111826] border-[#22304A]">
              <SelectItem value="all">All Outcomes</SelectItem>
              <SelectItem value="win">Wins</SelectItem>
              <SelectItem value="loss">Losses</SelectItem>
            </SelectContent>
          </Select>

          <Select value={filterAttribution} onValueChange={setFilterAttribution}>
            <SelectTrigger className="bg-[#111826] border-[#22304A] text-[#E7EEF9]">
              <SelectValue placeholder="Attribution" />
            </SelectTrigger>
            <SelectContent className="bg-[#111826] border-[#22304A]">
              <SelectItem value="all">All Attribution</SelectItem>
              <SelectItem value="A2_GOOD_EDGE">Good Edge</SelectItem>
              <SelectItem value="A0_LUCKY_WIN">Lucky Win</SelectItem>
              <SelectItem value="A1_BAD_MODEL">Bad Model</SelectItem>
              <SelectItem value="A3_BAD_EXECUTION">Bad Execution</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Trades List */}
        <ScrollArea className="h-[calc(100vh-300px)]">
          <div className="space-y-2">
            {trades.map((trade) => {
              const isSelected = selectedTrade?.trade_id === trade.trade_id;
              const isProfit = (trade.pnl || 0) > 0;

              return (
                <div
                  key={trade.trade_id}
                  onClick={() => setSelectedTrade(trade)}
                  className={cn(
                    'p-4 rounded-lg border cursor-pointer transition-all',
                    isSelected
                      ? 'bg-[#162033] border-[#B38BFF]'
                      : 'bg-[#111826] border-[#22304A] hover:border-[#B38BFF]'
                  )}
                >
                  <div className="space-y-3">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <div className="text-xs text-[#7F93B2] font-mono">
                          {trade.trade_id}
                        </div>
                        <div className="text-xs text-[#B8C7E0] mt-1">
                          {formatTime(trade.entry_time)}
                        </div>
                      </div>
                      {trade.template && (
                        <div className="px-2 py-1 bg-[#285A8F] text-[#4DA3FF] rounded text-xs">
                          {trade.template}
                        </div>
                      )}
                    </div>

                    {/* PnL */}
                    {trade.pnl !== undefined && (
                      <div className="flex items-center gap-2">
                        {isProfit ? (
                          <TrendingUp className="w-4 h-4 text-[#2ED47A]" />
                        ) : (
                          <TrendingDown className="w-4 h-4 text-[#FF5A5F]" />
                        )}
                        <span className={cn(
                          'text-lg font-semibold tabular-nums',
                          isProfit ? 'text-[#2ED47A]' : 'text-[#FF5A5F]'
                        )}>
                          {isProfit ? '+' : ''}{trade.pnl.toFixed(2)}
                        </span>
                      </div>
                    )}

                    {/* Duration */}
                    <div className="text-xs text-[#7F93B2]">
                      Duration: {getDuration(trade.entry_time, trade.exit_time)}
                    </div>

                    {/* Attribution Classification */}
                    {trade.attribution && (
                      <div className={cn(
                        'text-xs px-2 py-1 rounded',
                        trade.attribution.classification.includes('GOOD') && 'bg-[#1A7A45] text-[#2ED47A]',
                        trade.attribution.classification.includes('LUCKY') && 'bg-[#8B5A00] text-[#FFB020]',
                        trade.attribution.classification.includes('BAD') && 'bg-[#8B2C2F] text-[#FF5A5F]'
                      )}>
                        {trade.attribution.classification.replace(/_/g, ' ')}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </div>

      {/* Right: Trade Detail & Attribution */}
      <div className="col-span-8 space-y-6">
        {selectedTrade ? (
          <>
            {/* Trade Timeline */}
            <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6">
              <h3 className="font-semibold text-[#E7EEF9] mb-4">Trade Timeline</h3>
              
              <div className="space-y-4">
                {/* Entry */}
                <div className="flex items-start gap-4">
                  <div className="w-2 h-2 rounded-full bg-[#4DA3FF] mt-2"></div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-[#E7EEF9]">Entry</div>
                        <div className="text-xs text-[#7F93B2] mt-1">
                          {formatTime(selectedTrade.entry_time)}
                        </div>
                      </div>
                      {selectedTrade.fills[0] && (
                        <div className="text-sm text-[#E7EEF9] font-mono tabular-nums">
                          @ {selectedTrade.fills[0].fill_price?.toFixed(2)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Management (other fills) */}
                {selectedTrade.fills.slice(1, -1).map((fill, i) => (
                  <div key={i} className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-[#9AA9C2] mt-2"></div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-sm text-[#E7EEF9]">{fill.type}</div>
                          <div className="text-xs text-[#7F93B2] mt-1">
                            {fill.fill_time ? formatTime(fill.fill_time) : 'Pending'}
                          </div>
                        </div>
                        {fill.fill_price && (
                          <div className="text-sm text-[#E7EEF9] font-mono tabular-nums">
                            @ {fill.fill_price.toFixed(2)}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {/* Exit */}
                {selectedTrade.exit_time && selectedTrade.fills[selectedTrade.fills.length - 1] && (
                  <div className="flex items-start gap-4">
                    <div className="w-2 h-2 rounded-full bg-[#2ED47A] mt-2"></div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-sm text-[#E7EEF9]">Exit</div>
                          <div className="text-xs text-[#7F93B2] mt-1">
                            {formatTime(selectedTrade.exit_time)}
                          </div>
                        </div>
                        <div className="text-sm text-[#E7EEF9] font-mono tabular-nums">
                          @ {selectedTrade.fills[selectedTrade.fills.length - 1].fill_price?.toFixed(2)}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* PnL */}
            {selectedTrade.pnl !== undefined && (
              <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6">
                <div className="text-xs text-[#7F93B2] mb-2">Profit & Loss</div>
                <div className={cn(
                  'text-4xl font-semibold tabular-nums',
                  selectedTrade.pnl > 0 ? 'text-[#2ED47A]' : 'text-[#FF5A5F]'
                )}>
                  {selectedTrade.pnl > 0 ? '+' : ''}${selectedTrade.pnl.toFixed(2)}
                </div>
                <div className="text-sm text-[#7F93B2] mt-1">
                  Note: PnL is NOT the primary metric — focus on attribution quality
                </div>
              </div>
            )}

            {/* Attribution */}
            {selectedTrade.attribution && (
              <AttributionCard attribution={selectedTrade.attribution} />
            )}
          </>
        ) : (
          <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6">
            <div className="text-center text-[#7F93B2] py-12">
              Select a trade to view details and attribution
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
