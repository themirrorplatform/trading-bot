/**
 * Data Access Layer - Queries
 * 
 * Read models for fetching data from Supabase.
 * Use this instead of calling supabase directly in components.
 */

import { supabase } from '../supabase';
import type { Database } from '../supabase/types';

type Event = Database['public']['Tables']['events']['Row'];
type DecisionJournal = Database['public']['Tables']['decision_journal']['Row'];
type Trade = Database['public']['Tables']['trades']['Row'];

export interface LiveCockpitData {
  events: Event[];
  latestDecision: DecisionJournal | null;
  systemState: any; // TODO: type this properly
  marketData: any; // TODO: type this properly
}

/**
 * Fetch latest events for the live cockpit timeline
 */
export async function fetchLiveEvents(streamId: string = 'MES_RTH', limit: number = 100) {
  const { data, error } = await supabase
    .from('events')
    .select('*')
    .eq('stream_id', streamId)
    .order('timestamp', { ascending: false })
    .limit(limit);

  if (error) {
    console.error('Error fetching events:', error);
    return [];
  }

  return data || [];
}

/**
 * Fetch latest decision for the decision frame
 */
export async function fetchLatestDecision(streamId: string = 'MES_RTH') {
  const { data, error } = await supabase
    .from('decision_journal')
    .select('*')
    .eq('stream_id', streamId)
    .order('timestamp', { ascending: false })
    .limit(1)
    .single();

  if (error && error.code !== 'PGRST116') { // PGRST116 = no rows
    console.error('Error fetching latest decision:', error);
    return null;
  }

  return data;
}

/**
 * Fetch latest DECISION_1M event for gate trace
 */
export async function fetchLatestDecisionEvent(streamId: string = 'MES_RTH') {
  const { data, error } = await supabase
    .from('events')
    .select('*')
    .eq('stream_id', streamId)
    .eq('event_type', 'DECISION_1M')
    .order('timestamp', { ascending: false })
    .limit(1)
    .single();

  if (error && error.code !== 'PGRST116') {
    console.error('Error fetching latest decision event:', error);
    return null;
  }

  return data;
}

/**
 * Fetch latest BELIEFS_1M event
 */
export async function fetchLatestBeliefs(streamId: string = 'MES_RTH') {
  const { data, error } = await supabase
    .from('events')
    .select('*')
    .eq('stream_id', streamId)
    .eq('event_type', 'BELIEFS_1M')
    .order('timestamp', { ascending: false })
    .limit(1)
    .single();

  if (error && error.code !== 'PGRST116') {
    console.error('Error fetching latest beliefs:', error);
    return null;
  }

  return data;
}

/**
 * Fetch recent trades for attribution panel
 */
export async function fetchRecentTrades(streamId: string = 'MES_RTH', limit: number = 20) {
  const { data, error } = await supabase
    .from('trades')
    .select('*')
    .eq('stream_id', streamId)
    .order('entry_time', { ascending: false })
    .limit(limit);

  if (error) {
    console.error('Error fetching trades:', error);
    return [];
  }

  return data || [];
}

/**
 * Fetch events of a specific type
 */
export async function fetchEventsByType(
  streamId: string = 'MES_RTH',
  eventType: string,
  limit: number = 100
) {
  const { data, error } = await supabase
    .from('events')
    .select('*')
    .eq('stream_id', streamId)
    .eq('event_type', eventType)
    .order('timestamp', { ascending: false })
    .limit(limit);

  if (error) {
    console.error(`Error fetching ${eventType} events:`, error);
    return [];
  }

  return data || [];
}

/**
 * Fetch all live cockpit data in one call
 */
export async function fetchLiveCockpitData(streamId: string = 'MES_RTH'): Promise<LiveCockpitData> {
  const [events, latestDecision] = await Promise.all([
    fetchLiveEvents(streamId, 100),
    fetchLatestDecision(streamId),
  ]);

  // System state would come from a status table or computed view
  // For now, return a placeholder
  const systemState = {
    killSwitch: { status: 'ARMED' },
    connectionStatus: 'LIVE',
    equity: 1000,
    position: 0,
    pnl: 0,
  };

  // Market data would come from latest bar/signal event
  const marketData = {
    symbol: 'MES',
    price: 0,
    timestamp: new Date().toISOString(),
  };

  return {
    events,
    latestDecision,
    systemState,
    marketData,
  };
}
