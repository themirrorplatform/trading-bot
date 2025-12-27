/**
 * Custom Hook: useLiveCockpitData
 * 
 * Fetches and subscribes to live cockpit data with automatic fallback to mock.
 */

import { useState, useEffect } from 'react';
import { isUsingLiveData } from '../lib/data/config';
import { fetchLiveCockpitData, fetchLiveEvents, fetchLatestDecision } from '../lib/data/queries';
import { subscribeToEvents, unsubscribe } from '../lib/data/realtime';
import type { RealtimeChannel } from '@supabase/supabase-js';

// Import mock data as fallback
import {
  mockCompleteEvents,
  mockSkipDecision,
} from './data/mockData';

interface UseLiveCockpitDataOptions {
  streamId?: string;
  pollInterval?: number; // milliseconds, for polling when realtime is not available
}

export function useLiveCockpitData(options: UseLiveCockpitDataOptions = {}) {
  const { streamId = 'MES_RTH', pollInterval = 5000 } = options;
  
  const [events, setEvents] = useState<any[]>(mockCompleteEvents);
  const [currentDecision, setCurrentDecision] = useState<any>(mockSkipDecision);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!isUsingLiveData()) {
      // Use mock data
      return;
    }

    let channel: RealtimeChannel | null = null;
    let pollTimer: NodeJS.Timeout | null = null;

    // Initial fetch
    const fetchData = async () => {
      setLoading(true);
      try {
        const [eventsData, decisionData] = await Promise.all([
          fetchLiveEvents(streamId),
          fetchLatestDecision(streamId),
        ]);

        setEvents(eventsData);
        setCurrentDecision(decisionData);
        setError(null);
      } catch (err) {
        console.error('Error fetching live data:', err);
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    // Subscribe to realtime updates
    channel = subscribeToEvents(streamId, {
      onEvent: (newEvent) => {
        setEvents((prev) => [newEvent, ...prev].slice(0, 100)); // Keep last 100
      },
      onDecision: (decisionEvent) => {
        // Update current decision from the event payload
        setCurrentDecision(decisionEvent.payload);
      },
    });

    // Fallback: poll for updates if realtime doesn't work
    pollTimer = setInterval(fetchData, pollInterval);

    // Cleanup
    return () => {
      if (channel) {
        unsubscribe(channel);
      }
      if (pollTimer) {
        clearInterval(pollTimer);
      }
    };
  }, [streamId, pollInterval]);

  return {
    events,
    currentDecision,
    loading,
    error,
    isLive: isUsingLiveData(),
  };
}
