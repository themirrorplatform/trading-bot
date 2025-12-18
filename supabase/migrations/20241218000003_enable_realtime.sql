-- Enable Realtime for all bot tables
-- This allows the UI to subscribe to live updates via WebSocket

-- Enable Realtime publication for bot_events
ALTER PUBLICATION supabase_realtime ADD TABLE bot_events;

-- Enable Realtime publication for bot_latest_snapshot
ALTER PUBLICATION supabase_realtime ADD TABLE bot_latest_snapshot;

-- Enable Realtime publication for bot_health
ALTER PUBLICATION supabase_realtime ADD TABLE bot_health;

-- Add comments
COMMENT ON TABLE bot_events IS 'Realtime enabled: UI receives INSERT events as they happen';
COMMENT ON TABLE bot_latest_snapshot IS 'Realtime enabled: UI receives UPDATE events on state changes';
COMMENT ON TABLE bot_health IS 'Realtime enabled: UI receives UPDATE events on health changes';
