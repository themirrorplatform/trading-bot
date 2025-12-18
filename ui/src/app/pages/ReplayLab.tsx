import React, { useState } from 'react';
import { cn } from '../components/ui/utils';
import { DecisionCard } from '../components/DecisionCard';
import { Input } from '../components/ui/input';
import { Slider } from '../components/ui/slider';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Play, Pause, SkipBack, SkipForward, ChevronLeft, ChevronRight } from 'lucide-react';
import type { DecisionRecord } from '../types/trading-types';

interface ReplayLabProps {
  decisions: DecisionRecord[];
}

export function ReplayLab({ decisions }: ReplayLabProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [compareMode, setCompareMode] = useState(false);
  const [compareIndex, setCompareIndex] = useState(0);

  const currentDecision = decisions[currentIndex] || null;
  const compareDecision = compareMode ? decisions[compareIndex] || null : null;

  const handleStepForward = () => {
    if (currentIndex < decisions.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  const handleStepBackward = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  const handleJumpToStart = () => {
    setCurrentIndex(0);
  };

  const handleJumpToEnd = () => {
    setCurrentIndex(decisions.length - 1);
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  return (
    <div className="h-full p-6 space-y-6">
      {/* Header */}
      <div>
        <h2 className="font-semibold text-[#E7EEF9] mb-1">Replay Lab</h2>
        <p className="text-sm text-[#7F93B2]">Forensics: replay, compare, and analyze decisions</p>
      </div>

      <Tabs defaultValue="replay" className="w-full">
        <TabsList className="bg-[#111826] border border-[#22304A]">
          <TabsTrigger value="replay">Replay</TabsTrigger>
          <TabsTrigger value="compare">Compare</TabsTrigger>
          <TabsTrigger value="counterfactual">Counterfactual</TabsTrigger>
        </TabsList>

        {/* Replay Tab */}
        <TabsContent value="replay" className="space-y-6 mt-6">
          {/* Playback Controls */}
          <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-[#7F93B2] mb-1">Current Decision</div>
                <div className="text-sm text-[#E7EEF9] font-mono">
                  {currentDecision ? formatTimestamp(currentDecision.timestamp) : 'No decision selected'}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleJumpToStart}
                  className="p-2 bg-[#162033] border border-[#22304A] rounded hover:border-[#B38BFF] transition-colors"
                  disabled={currentIndex === 0}
                >
                  <SkipBack className="w-4 h-4 text-[#B8C7E0]" />
                </button>
                <button
                  onClick={handleStepBackward}
                  className="p-2 bg-[#162033] border border-[#22304A] rounded hover:border-[#B38BFF] transition-colors"
                  disabled={currentIndex === 0}
                >
                  <ChevronLeft className="w-4 h-4 text-[#B8C7E0]" />
                </button>
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="p-2 bg-[#B38BFF] border border-[#B38BFF] rounded hover:bg-[#9B6FFF] transition-colors"
                >
                  {isPlaying ? (
                    <Pause className="w-4 h-4 text-[#0B0F14]" />
                  ) : (
                    <Play className="w-4 h-4 text-[#0B0F14]" />
                  )}
                </button>
                <button
                  onClick={handleStepForward}
                  className="p-2 bg-[#162033] border border-[#22304A] rounded hover:border-[#B38BFF] transition-colors"
                  disabled={currentIndex === decisions.length - 1}
                >
                  <ChevronRight className="w-4 h-4 text-[#B8C7E0]" />
                </button>
                <button
                  onClick={handleJumpToEnd}
                  className="p-2 bg-[#162033] border border-[#22304A] rounded hover:border-[#B38BFF] transition-colors"
                  disabled={currentIndex === decisions.length - 1}
                >
                  <SkipForward className="w-4 h-4 text-[#B8C7E0]" />
                </button>
              </div>
            </div>

            {/* Timeline Scrubber */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-[#7F93B2]">
                <span>Decision {currentIndex + 1} of {decisions.length}</span>
                <span>Playback: {playbackSpeed}x</span>
              </div>
              <Slider
                value={[currentIndex]}
                onValueChange={([value]) => setCurrentIndex(value)}
                max={decisions.length - 1}
                step={1}
                className="w-full"
              />
            </div>

            {/* Event ID Input */}
            <div className="pt-4 border-t border-[#22304A]">
              <div className="text-xs text-[#7F93B2] mb-2">Jump to Event ID</div>
              <div className="flex gap-2">
                <Input
                  placeholder="evt_001"
                  className="bg-[#162033] border-[#22304A] text-[#E7EEF9]"
                />
                <button className="px-4 py-2 bg-[#B38BFF] text-[#0B0F14] rounded hover:bg-[#9B6FFF] transition-colors">
                  Jump
                </button>
              </div>
            </div>
          </div>

          {/* Reconstructed Decision */}
          <div className="grid grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium text-[#E7EEF9] mb-4">Reconstructed State</h3>
              <DecisionCard decision={currentDecision} />
            </div>

            <div>
              <h3 className="font-medium text-[#E7EEF9] mb-4">Snapshot Details</h3>
              <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6 space-y-4">
                <div>
                  <div className="text-xs text-[#7F93B2] mb-2">Bars Context</div>
                  <div className="text-sm text-[#E7EEF9] bg-[#162033] p-3 rounded font-mono">
                    Last bar: 4567.25 (+0.75)
                    <br />
                    Volume: 1,234
                    <br />
                    Session: RTH
                  </div>
                </div>

                <div>
                  <div className="text-xs text-[#7F93B2] mb-2">Signals Snapshot</div>
                  <div className="text-sm text-[#E7EEF9] bg-[#162033] p-3 rounded">
                    28 signals computed
                    <br />
                    3 signals updated
                    <br />
                    Avg reliability: 0.78
                  </div>
                </div>

                <div>
                  <div className="text-xs text-[#7F93B2] mb-2">Beliefs Snapshot</div>
                  <div className="text-sm text-[#E7EEF9] bg-[#162033] p-3 rounded">
                    Top constraint: C_MOMENTUM_REGIME (0.78)
                    <br />
                    Belief stability: 0.92
                    <br />
                    Decay state: 0.95
                  </div>
                </div>

                <div>
                  <div className="text-xs text-[#7F93B2] mb-2">Orders Snapshot</div>
                  <div className="text-sm text-[#E7EEF9] bg-[#162033] p-3 rounded">
                    {currentDecision?.proposed_order ? (
                      <>
                        Entry: {currentDecision.proposed_order.entry_price.toFixed(2)}
                        <br />
                        Stop: {currentDecision.proposed_order.stop_price.toFixed(2)}
                        <br />
                        Size: {currentDecision.proposed_order.position_size}
                      </>
                    ) : (
                      'No order proposed'
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Compare Tab */}
        <TabsContent value="compare" className="space-y-6 mt-6">
          <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6">
            <h3 className="font-medium text-[#E7EEF9] mb-4">Compare Two Decisions</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-[#7F93B2] mb-2">Decision A</div>
                <select className="w-full bg-[#162033] border border-[#22304A] rounded p-2 text-[#E7EEF9]">
                  {decisions.map((d, i) => (
                    <option key={i} value={i}>
                      {formatTimestamp(d.timestamp)} - {d.outcome}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <div className="text-xs text-[#7F93B2] mb-2">Decision B</div>
                <select className="w-full bg-[#162033] border border-[#22304A] rounded p-2 text-[#E7EEF9]">
                  {decisions.map((d, i) => (
                    <option key={i} value={i}>
                      {formatTimestamp(d.timestamp)} - {d.outcome}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium text-[#E7EEF9] mb-4">Decision A</h3>
              <DecisionCard decision={currentDecision} />
            </div>
            <div>
              <h3 className="font-medium text-[#E7EEF9] mb-4">Decision B</h3>
              <DecisionCard decision={compareDecision} />
            </div>
          </div>

          {/* Divergence Analysis */}
          <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6">
            <h3 className="font-medium text-[#E7EEF9] mb-4">Divergence Analysis</h3>
            <div className="space-y-3">
              <div className="p-3 bg-[#162033] rounded">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[#E7EEF9]">EUC Score</span>
                  <div className="flex gap-4 text-xs font-mono tabular-nums">
                    <span className="text-[#B8C7E0]">A: 2.30</span>
                    <span className="text-[#B8C7E0]">B: 4.15</span>
                    <span className="text-[#2ED47A]">Δ: +1.85</span>
                  </div>
                </div>
              </div>
              <div className="p-3 bg-[#162033] rounded">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[#E7EEF9]">Edge Component</span>
                  <div className="flex gap-4 text-xs font-mono tabular-nums">
                    <span className="text-[#B8C7E0]">A: 5.20</span>
                    <span className="text-[#B8C7E0]">B: 6.10</span>
                    <span className="text-[#2ED47A]">Δ: +0.90</span>
                  </div>
                </div>
              </div>
              <div className="p-3 bg-[#162033] rounded">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[#E7EEF9]">Outcome</span>
                  <div className="flex gap-4 text-xs">
                    <span className="text-[#B8C7E0]">A: SKIP</span>
                    <span className="text-[#B8C7E0]">B: TRADE</span>
                    <span className="text-[#FF5A5F]">CHANGED</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Counterfactual Tab */}
        <TabsContent value="counterfactual" className="space-y-6 mt-6">
          <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6 space-y-4">
            <h3 className="font-medium text-[#E7EEF9]">Counterfactual Playground</h3>
            <p className="text-sm text-[#7F93B2]">
              Modify one variable and see how the decision would change. This is SIMULATED (NON-LIVE).
            </p>

            {/* Variable Controls */}
            <div className="grid grid-cols-2 gap-6 pt-4">
              <div className="space-y-4">
                <div>
                  <div className="text-xs text-[#7F93B2] mb-2">Friction Model</div>
                  <select className="w-full bg-[#162033] border border-[#22304A] rounded p-2 text-[#E7EEF9]">
                    <option value="optimistic">Optimistic</option>
                    <option value="realistic" selected>Realistic</option>
                    <option value="pessimistic">Pessimistic</option>
                  </select>
                </div>

                <div>
                  <div className="text-xs text-[#7F93B2] mb-2">Reliability Scaling</div>
                  <Slider defaultValue={[100]} max={150} min={50} step={5} />
                  <div className="text-xs text-[#7F93B2] mt-1 text-center">100%</div>
                </div>

                <div>
                  <div className="text-xs text-[#7F93B2] mb-2">Gate Threshold Override</div>
                  <Input
                    type="number"
                    placeholder="e.g., 4.75"
                    className="bg-[#162033] border-[#22304A] text-[#E7EEF9]"
                  />
                </div>
              </div>

              <div className="bg-[#162033] rounded-lg p-4">
                <div className="text-xs text-[#7F93B2] mb-3">Simulated Output</div>
                <div className="space-y-3">
                  <div>
                    <div className="text-xs text-[#7F93B2]">New EUC Score</div>
                    <div className="text-2xl font-semibold text-[#E7EEF9] tabular-nums">3.45</div>
                    <div className="text-xs text-[#2ED47A]">+1.15 from original</div>
                  </div>
                  <div>
                    <div className="text-xs text-[#7F93B2]">Decision Change</div>
                    <div className="text-sm text-[#E7EEF9]">SKIP → TRADE</div>
                  </div>
                  <div>
                    <div className="text-xs text-[#7F93B2]">Gate Flipped</div>
                    <div className="text-sm text-[#E7EEF9]">GATE_FRICTION_TOO_HIGH</div>
                  </div>
                  <div>
                    <div className="text-xs text-[#7F93B2]">Position Size</div>
                    <div className="text-sm text-[#E7EEF9] font-mono">2 contracts</div>
                  </div>
                </div>
              </div>
            </div>

            <button className="w-full px-4 py-3 bg-[#B38BFF] text-[#0B0F14] rounded hover:bg-[#9B6FFF] transition-colors">
              Re-run Decision Engine
            </button>
          </div>

          {/* Warning */}
          <div className="bg-[#8B5A00]/10 border border-[#FFB020]/20 rounded-xl p-4 text-sm text-[#FFB020]">
            ⚠ SIMULATED (NON-LIVE): This is a read-only simulation. No actual trades or system state changes occur.
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
