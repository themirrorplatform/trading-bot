/**
 * Trading Bot Cockpit - COMPLETE APPLICATION
 * Demonstrates full epistemic transparency - all 24 success criteria met
 */

import { useState } from 'react';
import { LiveCockpitComplete } from './components/LiveCockpitComplete';
import { DemoControlsDrawer } from './components/DemoControlsDrawer';
import {
  mockSystemState,
  mockMarketData,
  mockSkipDecision,
  mockTradeDecision,
  mockHaltDecision,
  mockLiveGates,
  mockBlockingGates,
  mockWhatWouldChange
} from './data/mockData';
import {
  mockBeliefs,
  mockCompleteEvents,
  mockDriftAlerts,
  mockAttribution,
  mockExecutionBlame,
  mockManualActions,
  mockAnnotations,
  mockDataQuality,
  mockLiveGatesAllPass
} from './data/comprehensiveMockData';

export default function App() {
  const [systemState, setSystemState] = useState(mockSystemState);
  const [decisionType, setDecisionType] = useState<'SKIP' | 'TRADE' | 'HALT'>('SKIP');
  const [connectionStatus, setConnectionStatus] = useState<'LIVE' | 'DEGRADED' | 'DISCONNECTED' | 'CATCHUP'>('LIVE');
  const [showDriftAlerts, setShowDriftAlerts] = useState(true);
  const [showAttribution, setShowAttribution] = useState(true);
  const [annotations, setAnnotations] = useState(mockAnnotations);

  // Handle annotation add
  const handleAddAnnotation = (annotation: Omit<typeof mockAnnotations[0], 'id' | 'timestamp'>) => {
    const newAnnotation = {
      ...annotation,
      id: `annotation_${Date.now()}`,
      timestamp: new Date().toISOString()
    };
    setAnnotations([newAnnotation, ...annotations]);
  };

  // Handle annotation edit
  const handleEditAnnotation = (id: string, annotation: Omit<typeof mockAnnotations[0], 'id' | 'timestamp'>) => {
    setAnnotations(annotations.map(a => 
      a.id === id 
        ? { ...a, ...annotation, timestamp: new Date().toISOString() } 
        : a
    ));
  };

  // Handle annotation delete
  const handleDeleteAnnotation = (id: string) => {
    setAnnotations(annotations.filter(a => a.id !== id));
  };

  // Select the appropriate decision and gates based on state
  const getCurrentDecision = () => {
    switch (decisionType) {
      case 'TRADE':
        return mockTradeDecision;
      case 'HALT':
        return mockHaltDecision;
      default:
        return mockSkipDecision;
    }
  };

  const getCurrentGates = () => {
    return decisionType === 'TRADE' ? mockLiveGatesAllPass : mockLiveGates;
  };

  // Handle kill switch reset
  const handleKillSwitchReset = () => {
    setSystemState({
      ...systemState,
      killSwitch: {
        status: 'ARMED',
        reason: undefined,
        timestamp: undefined,
        operator: undefined
      }
    });
  };

  return (
    <div className="relative">
      {/* State Control Panel (for demonstration) */}
      <DemoControlsDrawer
        decisionType={decisionType}
        setDecisionType={setDecisionType}
        connectionStatus={connectionStatus}
        setConnectionStatus={setConnectionStatus}
        systemState={systemState}
        setSystemState={setSystemState}
        showDriftAlerts={showDriftAlerts}
        setShowDriftAlerts={setShowDriftAlerts}
        showAttribution={showAttribution}
        setShowAttribution={setShowAttribution}
        annotations={annotations}
        setAnnotations={setAnnotations}
        handleAddAnnotation={handleAddAnnotation}
        handleEditAnnotation={handleEditAnnotation}
        handleDeleteAnnotation={handleDeleteAnnotation}
        handleKillSwitchReset={handleKillSwitchReset}
      />

      {/* Live Cockpit - COMPLETE */}
      <LiveCockpitComplete
        systemState={{
          ...systemState,
          connectionStatus
        }}
        marketData={mockMarketData}
        currentDecision={getCurrentDecision()}
        events={mockCompleteEvents}
        liveGates={getCurrentGates()}
        blockingGates={decisionType === 'SKIP' ? mockBlockingGates : []}
        whatWouldChange={decisionType === 'SKIP' ? mockWhatWouldChange : []}
        beliefs={mockBeliefs}
        driftAlerts={showDriftAlerts ? mockDriftAlerts : []}
        attribution={showAttribution ? mockAttribution : undefined}
        executionBlame={showAttribution ? mockExecutionBlame : undefined}
        manualActions={mockManualActions}
        annotations={annotations}
        dataQuality={mockDataQuality}
        showTemporalGap={connectionStatus === 'CATCHUP' ? { duration: 45, reason: 'Reconnecting to feed' } : undefined}
        onAddAnnotation={handleAddAnnotation}
        onEditAnnotation={handleEditAnnotation}
        onDeleteAnnotation={handleDeleteAnnotation}
      />
    </div>
  );
}