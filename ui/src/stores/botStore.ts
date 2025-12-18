import { create } from 'zustand';
import { BotEvent, BotSnapshot, BotHealth } from '../lib/types';
import { supabase } from '../lib/supabase';

interface BotStore {
  // State
  deviceId: string;
  events: BotEvent[];
  snapshot: BotSnapshot | null;
  health: BotHealth | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  setDeviceId: (id: string) => void;
  addEvent: (event: BotEvent) => void;
  setSnapshot: (snapshot: BotSnapshot) => void;
  setHealth: (health: BotHealth) => void;
  setAuthenticated: (auth: boolean) => void;
  setLoading: (loading: boolean) => void;
  
  // Subscriptions
  subscribeToEvents: () => () => void;
  subscribeToSnapshot: () => () => void;
  subscribeToHealth: () => () => void;
}

export const useBotStore = create<BotStore>((set, get) => ({
  // Initial state
  deviceId: import.meta.env.VITE_DEFAULT_DEVICE_ID || 'bot-01',
  events: [],
  snapshot: null,
  health: null,
  isAuthenticated: false,
  isLoading: true,

  // Actions
  setDeviceId: (id) => set({ deviceId: id }),
  
  addEvent: (event) =>
    set((state) => ({
      events: [event, ...state.events].slice(0, 100), // Keep last 100 events
    })),
  
  setSnapshot: (snapshot) => set({ snapshot }),
  
  setHealth: (health) => set({ health }),
  
  setAuthenticated: (auth) => set({ isAuthenticated: auth }),
  
  setLoading: (loading) => set({ isLoading: loading }),

  // Realtime subscriptions
  subscribeToEvents: () => {
    const { deviceId, addEvent } = get();
    
    const channel = supabase
      .channel('bot-events')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'bot_events',
          filter: `device_id=eq.${deviceId}`,
        },
        (payload) => {
          addEvent(payload.new as BotEvent);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  },

  subscribeToSnapshot: () => {
    const { deviceId, setSnapshot } = get();
    
    const channel = supabase
      .channel('bot-snapshot')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'bot_latest_snapshot',
          filter: `device_id=eq.${deviceId}`,
        },
        (payload) => {
          setSnapshot(payload.new as BotSnapshot);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  },

  subscribeToHealth: () => {
    const { deviceId, setHealth } = get();
    
    const channel = supabase
      .channel('bot-health')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'bot_health',
          filter: `device_id=eq.${deviceId}`,
        },
        (payload) => {
          setHealth(payload.new as BotHealth);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  },
}));
