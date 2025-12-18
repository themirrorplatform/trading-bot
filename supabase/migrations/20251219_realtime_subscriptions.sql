-- Realtime setup for Supabase Phase 2
-- Enable live subscriptions for UI clients

-- Enable realtime on bot_events for live timeline
ALTER PUBLICATION supabase_realtime ADD TABLE bot_events;

-- Enable realtime on bot_latest_snapshot for live state updates
ALTER PUBLICATION supabase_realtime ADD TABLE bot_latest_snapshot;

-- Enable realtime on bot_health for live health monitoring
ALTER PUBLICATION supabase_realtime ADD TABLE bot_health;

-- Create indexes for common filter patterns used by subscribers
CREATE INDEX IF NOT EXISTS bot_events_device_ts_idx 
ON bot_events(device_id, ts DESC)
WHERE type IN ('SIGNAL', 'DECISION', 'EXECUTION', 'BLAME');

CREATE INDEX IF NOT EXISTS bot_events_severity_idx 
ON bot_events(severity, ts DESC);

CREATE INDEX IF NOT EXISTS bot_health_device_idx 
ON bot_health(device_id);
