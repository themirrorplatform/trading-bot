// Supabase Edge Function: bot-ingest
// Receives data from the bot publisher and writes to Postgres
// Validates device authentication using shared secret

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

interface BotPayload {
  device_id: string;
  events?: Array<{
    id: string;
    event_type: string;
    timestamp: string;
    payload: Record<string, unknown>;
  }>;
  snapshot?: {
    timestamp: string;
    equity: number;
    position: number;
    unrealized_pnl: number;
    realized_pnl: number;
    daily_pnl: number;
    signals?: Record<string, unknown>;
    beliefs?: Record<string, unknown>;
  };
  health?: {
    timestamp: string;
    status: 'healthy' | 'degraded' | 'down';
    dvs: number;
    eqs: number;
    kill_switch_active: boolean;
    last_heartbeat: string;
  };
}

serve(async (req) => {
  // CORS headers
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  };

  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    // Verify shared secret for device authentication
    const authHeader = req.headers.get('Authorization');
    const expectedSecret = Deno.env.get('DEVICE_SHARED_SECRET');
    
    if (!authHeader || authHeader !== `Bearer ${expectedSecret}`) {
      return new Response(
        JSON.stringify({ error: 'Unauthorized' }),
        { 
          status: 401, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      );
    }

    // Parse payload
    const payload: BotPayload = await req.json();

    if (!payload.device_id) {
      return new Response(
        JSON.stringify({ error: 'Missing device_id' }),
        { 
          status: 400, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      );
    }

    // Initialize Supabase client with service role key
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
      {
        auth: {
          autoRefreshToken: false,
          persistSession: false,
        },
      }
    );

    const results: Record<string, unknown> = {};

    // Insert events if provided
    if (payload.events && payload.events.length > 0) {
      const eventsToInsert = payload.events.map(event => ({
        id: event.id,
        device_id: payload.device_id,
        event_type: event.event_type,
        timestamp: event.timestamp,
        payload: event.payload,
      }));

      const { error: eventsError } = await supabase
        .from('bot_events')
        .insert(eventsToInsert);

      if (eventsError) {
        console.error('Error inserting events:', eventsError);
        results.events_error = eventsError.message;
      } else {
        results.events_inserted = eventsToInsert.length;
      }
    }

    // Upsert snapshot if provided
    if (payload.snapshot) {
      const { error: snapshotError } = await supabase
        .from('bot_latest_snapshot')
        .upsert({
          device_id: payload.device_id,
          timestamp: payload.snapshot.timestamp,
          equity: payload.snapshot.equity,
          position: payload.snapshot.position,
          unrealized_pnl: payload.snapshot.unrealized_pnl,
          realized_pnl: payload.snapshot.realized_pnl,
          daily_pnl: payload.snapshot.daily_pnl,
          signals: payload.snapshot.signals,
          beliefs: payload.snapshot.beliefs,
        });

      if (snapshotError) {
        console.error('Error upserting snapshot:', snapshotError);
        results.snapshot_error = snapshotError.message;
      } else {
        results.snapshot_updated = true;
      }
    }

    // Upsert health if provided
    if (payload.health) {
      const { error: healthError } = await supabase
        .from('bot_health')
        .upsert({
          device_id: payload.device_id,
          timestamp: payload.health.timestamp,
          status: payload.health.status,
          dvs: payload.health.dvs,
          eqs: payload.health.eqs,
          kill_switch_active: payload.health.kill_switch_active,
          last_heartbeat: payload.health.last_heartbeat,
        });

      if (healthError) {
        console.error('Error upserting health:', healthError);
        results.health_error = healthError.message;
      } else {
        results.health_updated = true;
      }
    }

    return new Response(
      JSON.stringify({ success: true, results }),
      {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    console.error('Error processing request:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );
  }
});
