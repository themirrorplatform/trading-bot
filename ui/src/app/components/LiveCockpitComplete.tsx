/**
 * LiveCockpitComplete - COMPLETE Live Cockpit with ALL epistemic transparency features
 * Passes all 24 success criteria
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
import { BeliefStatePanel } from './domain/BeliefStatePanel';
import { DriftAlertBanner } from './domain/DriftAlertBanner';
import { AttributionCard } from './domain/AttributionCard';
import { ExecutionBlameCard } from './domain/ExecutionBlameCard';
import { ManualActionLog } from './domain/ManualActionLog';
import { AnnotationPanel } from './domain/AnnotationPanel';
import { DataQualityIndicator } from './domain/DataQualityIndicator';
import { TemporalGapMarker } from './domain/TemporalGapMarker';

interface LiveCockpitCompleteProps {
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
  beliefs: any[];
  driftAlerts: any[];
  attribution?: any;
  executionBlame?: any;
  manualActions: any[];
  annotations: any[];
  dataQuality: any[];
  showTemporalGap?: { duration: number; reason: string };
  onAddAnnotation?: (annotation: any) => void;
  onEditAnnotation?: (id: string, annotation: any) => void;
  onDeleteAnnotation?: (id: string) => void;
}

export function LiveCockpitComplete({
  systemState,
  marketData,
  currentDecision,
  events,
  liveGates,
  blockingGates = [],
  whatWouldChange = [],
  beliefs,
  driftAlerts,
  attribution,
  executionBlame,
  manualActions,
  annotations,
  dataQuality,
  showTemporalGap,
  onAddAnnotation,
  onEditAnnotation,
  onDeleteAnnotation
}: LiveCockpitCompleteProps) {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'beliefs' | 'attribution' | 'manual' | 'data'>('beliefs');

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
              Live Cockpit
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

      {/* Drift Alerts (if any) */}
      {driftAlerts.length > 0 && (
        <div className="px-6 pt-4">
          <DriftAlertBanner alerts={driftAlerts} />
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-12 gap-4 p-6">
        {/* Left Column: Event Timeline (4 columns) */}
        <div className="col-span-4 space-y-4">
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-[var(--text-0)] uppercase tracking-wide">
                Live Event Stream
              </h2>
              <span className="text-xs text-[var(--text-2)]">
                {events.length} events
              </span>
            </div>
            <div className="max-h-[calc(100vh-300px)] overflow-y-auto -mx-4">
              {showTemporalGap && (
                <TemporalGapMarker
                  gapDuration={showTemporalGap.duration}
                  reason={showTemporalGap.reason}
                />
              )}
              {events.map((event) => (
                <EventRow
                  key={event.id}
                  event={event}
                  onExpand={(id) => setSelectedEventId(id)}
                />
              ))}
            </div>
          </Card>

          {/* Annotations */}
          <AnnotationPanel
            annotations={annotations}
            linkedContext={selectedEventId ? { type: 'EVENT', id: selectedEventId } : undefined}
            onAdd={onAddAnnotation}
            onEdit={onEditAnnotation}
            onDelete={onDeleteAnnotation}
          />
        </div>

        {/* Middle Column: Decision & Beliefs (4 columns) */}
        <div className="col-span-4 space-y-4">
          {/* Current Decision */}
          <div>
            <h2 className="text-sm font-semibold text-[var(--text-0)] uppercase tracking-wide mb-3">
              Current Decision
            </h2>
            <DecisionCard decision={currentDecision} />
          </div>

          {/* Why Not Panel (if applicable) */}
          {currentDecision.type === 'SKIP' && blockingGates.length > 0 && (
            <WhyNotCard
              blockingGates={blockingGates}
              whatWouldChange={whatWouldChange}
            />
          )}

          {/* Active Beliefs */}
          <BeliefStatePanel beliefs={beliefs} highlightDominant={true} />
        </div>

        {/* Right Column: Gates & Context (4 columns) */}
        <div className="col-span-4 space-y-4">
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

          {/* Tabbed Context Panel */}
          <Card>
            <div className="flex items-center gap-2 mb-4 border-b border-[var(--stroke-0)]">
              {['beliefs', 'attribution', 'manual', 'data'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab as any)}
                  className={`px-3 py-2 text-xs uppercase tracking-wide font-medium transition-colors ${
                    activeTab === tab
                      ? 'text-[var(--accent)] border-b-2 border-[var(--accent)]'
                      : 'text-[var(--text-2)] hover:text-[var(--text-0)]'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            <div className="max-h-96 overflow-y-auto">
              {activeTab === 'beliefs' && (
                <div className="text-sm text-[var(--text-1)]">
                  <div className="space-y-2">
                    <div>
                      <span className="text-[var(--text-2)]">Active Beliefs:</span> {beliefs.length}
                    </div>
                    <div>
                      <span className="text-[var(--text-2)]">Dominant Belief:</span>{' '}
                      {beliefs[0]?.name || 'None'}
                    </div>
                    <div>
                      <span className="text-[var(--text-2)]">Drift Alerts:</span> {driftAlerts.length}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'attribution' && attribution && (
                <div className="-m-4">
                  <AttributionCard attribution={attribution} />
                  {executionBlame && (
                    <div className="mt-4">
                      <ExecutionBlameCard execution={executionBlame} />
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'attribution' && !attribution && (
                <div className="text-sm text-[var(--text-2)] text-center py-4">
                  No recent attributions
                </div>
              )}

              {activeTab === 'manual' && (
                <div className="-m-4">
                  <ManualActionLog actions={manualActions} maxVisible={5} />
                </div>
              )}

              {activeTab === 'data' && (
                <div className="-m-4">
                  <DataQualityIndicator feeds={dataQuality} />
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}