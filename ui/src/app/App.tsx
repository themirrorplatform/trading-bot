/**
 * Trading Bot Cockpit - COMPLETE APPLICATION WITH LIVE DATA
 * Connects to Supabase for real-time bot data or uses mock data fallback
 */

import { useState, useEffect } from 'react';
import { LiveCockpitComplete } from './components/LiveCockpitComplete';
import { DemoControlsDrawer } from './components/DemoControlsDrawer';
import { isUsingLiveData } from '../lib/data/config';
import { fetchLiveEvents, fetchLatestDecisionEvent, fetchLatestBeliefs } from '../lib/data/queries';
import { subscribeToEvents, unsubscribe } from '../lib/data/realtime';
import type { RealtimeChannel } from '@supabase/supabase-js';

// Import mock data as fallback
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
  // UI State
  const [systemState, setSystemState] = useState(mockSystemState);
  const [decisionType, setDecisionType] = useState<'SKIP' | 'TRADE' | 'HALT'>('SKIP');
  const [connectionStatus, setConnectionStatus] = useState<'LIVE' | 'DEGRADED' | 'DISCONNECTED' | 'CATCHUP'>(
    isUsingLiveData() ? 'LIVE' : 'DEGRADED'
  );
  const [showDriftAlerts, setShowDriftAlerts] = useState(true);
  const [showAttribution, setShowAttribution] = useState(true);
  const [annotations, setAnnotations] = useState(mockAnnotations);

  // Live Data State
  const [liveEvents, setLiveEvents] = useState(mockCompleteEvents);
  const [liveDecision, setLiveDecision] = useState(mockSkipDecision);
  const [liveBeliefs, setLiveBeliefs] = useState(mockBeliefs);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch live data on mount
  useEffect(() => {
    if (!isUsingLiveData()) {
      return; // Use mock data
    }

    let channel: RealtimeChannel | null = null;

    const fetchData = async () => {
      setIsLoading(true);
      try {
        const [events, decision, beliefs] = await Promise.all([
          fetchLiveEvents('MES_RTH', 100),
          fetchLatestDecisionEvent('MES_RTH'),
          fetchLatestBeliefs('MES_RTH'),
        ]);

        if (events.length > 0) {
          setLiveEvents(events.map(e => ({
            event_id: e.id,
            stream_id: e.stream_id,
            ts: e.timestamp,
            type: e.event_type,
            payload: e.payload as any,
            config_hash: e.config_hash,
            created_at: e.created_at,
          })));
        }

        if (decision) {
          setLiveDecision(decision.payload as any);
        }

        if (beliefs) {
          setLiveBeliefs(beliefs.payload as any);
        }

        setConnectionStatus('LIVE');
      } catch (error) {
        console.error('Error fetching live data:', error);
        setConnectionStatus('DEGRADED');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();

    // Subscribe to realtime updates
    channel = subscribeToEvents('MES_RTH', {
      onEvent: (newEvent) => {
        setLiveEvents((prev) => [{
          event_id: newEvent.id,
          stream_id: newEvent.stream_id,
          ts: newEvent.timestamp,
          type: newEvent.event_type,
          payload: newEvent.payload,
          config_hash: newEvent.config_hash,
          created_at: newEvent.created_at,
        }, ...prev].slice(0, 100));
      },
      onDecision: (decisionEvent) => {
        setLiveDecision(decisionEvent.payload);
      },
      onBelief: (beliefEvent) => {
        setLiveBeliefs(beliefEvent.payload);
      },
    });

    return () => {
      if (channel) {
        unsubscribe(channel);
      }
    };
  }, []);

  // Use live data if available, otherwise fall back to mock
  const events = isUsingLiveData() ? liveEvents : mockCompleteEvents;
  const currentBeliefs = isUsingLiveData() ? liveBeliefs : mockBeliefs;
  const currentDecision = isUsingLiveData() ? liveDecision : (
    decisionType === 'TRADE' ? mockTradeDecision :
    decisionType === 'HALT' ? mockHaltDecision :
    mockSkipDecision
  );

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading trading data...</p>
        </div>
      </div>
    );
  }

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

  // Get gates - use mock for now (TODO: implement gate detection from live events)
  const getCurrentGates = () => {
    return decisionType === 'TRADE' ? mockLiveGatesAllPass : mockLiveGates;
  };

  return (
    <div className="relative">
      {/* Connection Status Indicator */}
      {isUsingLiveData() && (
        <div className="fixed top-4 right-4 z-50 flex items-center gap-2 bg-white px-3 py-2 rounded-lg shadow-lg border">
          <div className={`w-2 h-2 rounded-full ${
            connectionStatus === 'LIVE' ? 'bg-green-500 animate-pulse' :
            connectionStatus === 'DEGRADED' ? 'bg-yellow-500' :
            'bg-red-500'
          }`} />
          <span className="text-sm font-medium">
            {connectionStatus === 'LIVE' ? 'Live Data' :
             connectionStatus === 'DEGRADED' ? 'Degraded' :
             connectionStatus === 'CATCHUP' ? 'Catching Up' :
             'Disconnected'}
          </span>
        </div>
      )}

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

      {/* Live Cockpit - NOW WITH REAL DATA */}
      <LiveCockpitComplete
        systemState={{
          ...systemState,
          connectionStatus
        }}
        marketData={mockMarketData}
        currentDecision={currentDecision}
        events={events}
        liveGates={getCurrentGates()}
        blockingGates={decisionType === 'SKIP' ? mockBlockingGates : []}
        whatWouldChange={decisionType === 'SKIP' ? mockWhatWouldChange : []}
        beliefs={currentBeliefs}
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