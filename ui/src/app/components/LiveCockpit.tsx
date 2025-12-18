/**
 * LiveCockpit - The main real-time monitoring screen
 * Shows everything the bot decides with full explainability
 */

import { useState } from 'react';
import { KillSwitchBanner } from './domain/KillSwitchBanner';
import { ConnectionStatus } from './domain/ConnectionStatus';
import { Badge } from './primitives/Badge';
import { EventRow } from './domain/EventRow';
import { DecisionCard } from './domain/DecisionCard';
import { WhyNotCard } from './domain/WhyNotCard';
import { GateResultRow } from './domain/GateResultRow';
import { Card } from './primitives/Card';
import { NumericValue } from './primitives/NumericValue';

interface LiveCockpitProps {
  // Mock data will be passed in
  systemState: {
    mode: 'OBSERVE' | 'PAPER' | 'LIVE';
    session: 'RTH' | 'ETH';
    connectionStatus: 'LIVE' | 'DEGRADED' | 'DISCONNECTED' | 'CATCHUP';
    killSwitch: {
      status: 'ARMED' | 'TRIPPED' | 'RESET_PENDING';
      reason?: string;
      timestamp?: string;
      operator?: string;
    };
  };
  marketData: {
    symbol: string;
    price: number;
    change: number;
    volume: number;
  };
  currentDecision: any;
  events: any[];
  liveGates: any[];
  blockingGates?: any[];
  whatWouldChange?: string[];
}

export function LiveCockpit({
  systemState,
  marketData,
  currentDecision,
  events,
  liveGates,
  blockingGates = [],
  whatWouldChange = []
}: LiveCockpitProps) {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-[var(--bg-0)]">
      {/* Kill Switch Banner */}
      <KillSwitchBanner
        status={systemState.killSwitch.status}
        reason={systemState.killSwitch.reason}
        timestamp={systemState.killSwitch.timestamp}
        operator={systemState.killSwitch.operator}
      />

      {/* Top App Bar */}
      <div className="sticky top-0 z-10 bg-[var(--bg-1)] border-b border-[var(--stroke-0)] px-6 py-3">
        <div className="flex items-center justify-between">
          {/* Left: System Info */}
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold text-[var(--text-0)]">
              Trading Cockpit
            </h1>
            <Badge variant="mode" type={systemState.mode}>
              {systemState.mode}
            </Badge>
            <Badge variant="session">
              {systemState.session}
            </Badge>
          </div>

          {/* Right: Market & Connection */}
          <div className="flex items-center gap-6">
            {/* Market Strip */}
            <div className="flex items-center gap-4">
              <div>
                <div className="text-xs text-[var(--text-2)]">Symbol</div>
                <div className="font-mono text-[var(--text-0)]">
                  {marketData.symbol}
                </div>
              </div>
              <div>
                <div className="text-xs text-[var(--text-2)]">Price</div>
                <div className="font-mono text-[var(--text-0)]">
                  <NumericValue value={marketData.price} decimals={2} />
                </div>
              </div>
              <div>
                <div className="text-xs text-[var(--text-2)]">Change</div>
                <div className="font-mono">
                  <NumericValue value={marketData.change} format="percentage" delta={true} />
                </div>
              </div>
              <div>
                <div className="text-xs text-[var(--text-2)]">Volume</div>
                <div className="font-mono text-[var(--text-0)]">
                  {marketData.volume.toLocaleString()}
                </div>
              </div>
            </div>

            <div className="h-8 w-px bg-[var(--stroke-0)]" />

            {/* Connection Status */}
            <ConnectionStatus status={systemState.connectionStatus} latency={12} />
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-12 gap-4 p-6">
        {/* Left: Event Timeline (5 columns) */}
        <div className="col-span-5 space-y-4">
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-[var(--text-0)] uppercase tracking-wide">
                Live Event Stream
              </h2>
              <span className="text-xs text-[var(--text-2)]">
                {events.length} events
              </span>
            </div>
            <div className="max-h-[calc(100vh-200px)] overflow-y-auto -mx-4">
              {events.map((event) => (
                <EventRow
                  key={event.id}
                  event={event}
                  onExpand={(id) => setSelectedEventId(id)}
                />
              ))}
            </div>
          </Card>
        </div>

        {/* Right Column (7 columns) */}
        <div className="col-span-7 space-y-4">
          {/* Current Decision */}
          <div>
            <h2 className="text-sm font-semibold text-[var(--text-0)] uppercase tracking-wide mb-3">
              Current Decision
            </h2>
            <DecisionCard decision={currentDecision} />
          </div>

          {/* Why Not Panel (if applicable) */}
          {currentDecision.type === 'SKIP' && blockingGates.length > 0 && (
            <div>
              <WhyNotCard
                blockingGates={blockingGates}
                whatWouldChange={whatWouldChange}
              />
            </div>
          )}

          {/* Live Gate Evaluations */}
          <div>
            <h2 className="text-sm font-semibold text-[var(--text-0)] uppercase tracking-wide mb-3">
              Live Gate Evaluations
            </h2>
            <Card>
              <div className="divide-y divide-[var(--stroke-1)]">
                {liveGates.map((gate, i) => (
                  <GateResultRow key={i} gate={gate} />
                ))}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
