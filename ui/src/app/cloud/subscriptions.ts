import { supabase } from './supabaseClient';

export type EventRow = {
  device_id: string;
  seq: number;
  event_id: string;
  ts: string;
  type: string;
  severity?: string;
  symbol?: string;
  session?: string;
  reason_codes?: string[];
  summary?: string;
  payload: unknown;
};

export type SnapshotRow = {
  device_id: string;
  updated_at: string;
  last_seq: number;
  snapshot: unknown;
};

export type HealthRow = {
  device_id: string;
  updated_at: string;
  mode: string;
  kill_switch: string;
  feed_latency_ms?: number;
  missing_bars?: number;
  clock_drift_ms?: number;
  notes?: string;
};

export function subscribeCloud(
  deviceId: string,
  handlers: {
    onEvent?: (row: EventRow) => void;
    onSnapshot?: (row: SnapshotRow) => void;
    onHealth?: (row: HealthRow) => void;
    onError?: (err: unknown) => void;
  }
) {
  const channel = supabase
    .channel(`bot-${deviceId}`)
    .on(
      'postgres_changes',
      { event: 'INSERT', schema: 'public', table: 'bot_events', filter: `device_id=eq.${deviceId}` },
      (payload) => {
        try {
          handlers.onEvent?.(payload.new as EventRow);
        } catch (e) {
          handlers.onError?.(e);
        }
      }
    )
    .on(
      'postgres_changes',
      { event: 'UPDATE', schema: 'public', table: 'bot_latest_snapshot', filter: `device_id=eq.${deviceId}` },
      (payload) => {
        try {
          handlers.onSnapshot?.(payload.new as SnapshotRow);
        } catch (e) {
          handlers.onError?.(e);
        }
      }
    )
    .on(
      'postgres_changes',
      { event: 'UPDATE', schema: 'public', table: 'bot_health', filter: `device_id=eq.${deviceId}` },
      (payload) => {
        try {
          handlers.onHealth?.(payload.new as HealthRow);
        } catch (e) {
          handlers.onError?.(e);
        }
      }
    );

  const sub = channel.subscribe((status) => {
    if (status === 'SUBSCRIBED') {
      // ok
    }
  });

  return {
    unsubscribe: async () => {
      try { await supabase.removeChannel(channel); } catch {}
    }
  };
}
