/**
 * Data Access Layer - Realtime Subscriptions
 * 
 * Set up realtime channels for live data updates.
 */

import { supabase } from '../supabase';
import type { RealtimeChannel } from '@supabase/supabase-js';

export interface EventSubscriptionCallbacks {
  onEvent?: (event: any) => void;
  onDecision?: (decision: any) => void;
  onBelief?: (belief: any) => void;
  onTrade?: (trade: any) => void;
}

/**
 * Subscribe to real-time events from the bot
 */
export function subscribeToEvents(
  streamId: string = 'MES_RTH',
  callbacks: EventSubscriptionCallbacks
): RealtimeChannel {
  const channel = supabase
    .channel(`events:${streamId}`)
    .on(
      'postgres_changes',
      {
        event: 'INSERT',
        schema: 'public',
        table: 'events',
        filter: `stream_id=eq.${streamId}`,
      },
      (payload) => {
        const event = payload.new;
        
        // Route to specific callbacks based on event_type
        if (callbacks.onEvent) {
          callbacks.onEvent(event);
        }

        if (event.event_type === 'DECISION_1M' && callbacks.onDecision) {
          callbacks.onDecision(event);
        }

        if (event.event_type === 'BELIEFS_1M' && callbacks.onBelief) {
          callbacks.onBelief(event);
        }
      }
    )
    .subscribe();

  return channel;
}

/**
 * Subscribe to real-time trades
 */
export function subscribeToTrades(
  streamId: string = 'MES_RTH',
  onTrade: (trade: any) => void
): RealtimeChannel {
  const channel = supabase
    .channel(`trades:${streamId}`)
    .on(
      'postgres_changes',
      {
        event: '*', // INSERT, UPDATE
        schema: 'public',
        table: 'trades',
        filter: `stream_id=eq.${streamId}`,
      },
      (payload) => {
        onTrade(payload.new);
      }
    )
    .subscribe();

  return channel;
}

/**
 * Unsubscribe from a channel
 */
export async function unsubscribe(channel: RealtimeChannel) {
  await supabase.removeChannel(channel);
}
