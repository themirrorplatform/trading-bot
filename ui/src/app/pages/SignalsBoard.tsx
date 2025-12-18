import React, { useState, useMemo } from 'react';
import { SignalTile } from '../components/SignalTile';
import { SignalDetailPanel } from '../components/SignalDetailPanel';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Search } from 'lucide-react';
import type { Signal, SignalCategory } from '../types/trading-types';

interface SignalsBoardProps {
  signals: Signal[];
}

export function SignalsBoard({ signals }: SignalsBoardProps) {
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [impactFilter, setImpactFilter] = useState<string>('all');
  const [freshnessFilter, setFreshnessFilter] = useState<string>('all');

  const filteredSignals = useMemo(() => {
    return signals.filter((signal) => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        if (
          !signal.signal_name.toLowerCase().includes(query) &&
          !signal.signal_code.toLowerCase().includes(query)
        ) {
          return false;
        }
      }

      // Category filter
      if (categoryFilter !== 'all' && signal.category !== categoryFilter) {
        return false;
      }

      // Impact filter
      if (impactFilter !== 'all') {
        if (impactFilter === 'high' && signal.impact_on_decision <= 7) return false;
        if (impactFilter === 'medium' && (signal.impact_on_decision <= 4 || signal.impact_on_decision > 7)) return false;
        if (impactFilter === 'low' && signal.impact_on_decision > 4) return false;
      }

      // Freshness filter
      if (freshnessFilter !== 'all') {
        if (freshnessFilter === 'recent' && signal.freshness_bars > 2) return false;
        if (freshnessFilter === 'stale' && signal.freshness_bars <= 2) return false;
      }

      return true;
    });
  }, [signals, searchQuery, categoryFilter, impactFilter, freshnessFilter]);

  return (
    <div className="h-full p-6 space-y-6">
      {/* Header */}
      <div>
        <h2 className="font-semibold text-[#E7EEF9] mb-1">Signals Board</h2>
        <p className="text-sm text-[#7F93B2]">
          {filteredSignals.length} of {signals.length} signals
        </p>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-4 gap-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#7F93B2]" />
          <Input
            placeholder="Search signals..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-[#111826] border-[#22304A] text-[#E7EEF9] placeholder:text-[#7F93B2]"
          />
        </div>

        {/* Category Filter */}
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="bg-[#111826] border-[#22304A] text-[#E7EEF9]">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent className="bg-[#111826] border-[#22304A]">
            <SelectItem value="all">All Categories</SelectItem>
            <SelectItem value="MOMENTUM">Momentum</SelectItem>
            <SelectItem value="VOLATILITY">Volatility</SelectItem>
            <SelectItem value="STRUCTURE">Structure</SelectItem>
            <SelectItem value="FLOW">Flow</SelectItem>
            <SelectItem value="REGIME">Regime</SelectItem>
            <SelectItem value="TIME">Time</SelectItem>
          </SelectContent>
        </Select>

        {/* Impact Filter */}
        <Select value={impactFilter} onValueChange={setImpactFilter}>
          <SelectTrigger className="bg-[#111826] border-[#22304A] text-[#E7EEF9]">
            <SelectValue placeholder="Impact" />
          </SelectTrigger>
          <SelectContent className="bg-[#111826] border-[#22304A]">
            <SelectItem value="all">All Impact Levels</SelectItem>
            <SelectItem value="high">High Impact</SelectItem>
            <SelectItem value="medium">Medium Impact</SelectItem>
            <SelectItem value="low">Low Impact</SelectItem>
          </SelectContent>
        </Select>

        {/* Freshness Filter */}
        <Select value={freshnessFilter} onValueChange={setFreshnessFilter}>
          <SelectTrigger className="bg-[#111826] border-[#22304A] text-[#E7EEF9]">
            <SelectValue placeholder="Freshness" />
          </SelectTrigger>
          <SelectContent className="bg-[#111826] border-[#22304A]">
            <SelectItem value="all">All Freshness</SelectItem>
            <SelectItem value="recent">Recent Only</SelectItem>
            <SelectItem value="stale">Stale Only</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Signal Grid */}
      {filteredSignals.length === 0 ? (
        <div className="text-center py-12 text-[#7F93B2]">
          No signals match your filters
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-4">
          {filteredSignals.map((signal) => (
            <SignalTile
              key={signal.signal_id}
              signal={signal}
              onClick={() => setSelectedSignal(signal)}
            />
          ))}
        </div>
      )}

      {/* Detail Panel */}
      <SignalDetailPanel
        signal={selectedSignal}
        open={selectedSignal !== null}
        onClose={() => setSelectedSignal(null)}
      />
    </div>
  );
}
