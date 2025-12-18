-- Audit and retention policies
-- Track write audit trail, cleanup old data

-- Audit table for write operations
CREATE TABLE IF NOT EXISTS bot_audit_log (
  id BIGSERIAL PRIMARY KEY,
  table_name TEXT NOT NULL,
  operation TEXT NOT NULL,
  device_id TEXT,
  recorded_at TIMESTAMPTZ DEFAULT NOW(),
  user_id UUID DEFAULT auth.uid(),
  changes JSONB
);

CREATE INDEX IF NOT EXISTS bot_audit_log_device_idx 
ON bot_audit_log(device_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS bot_audit_log_operation_idx 
ON bot_audit_log(operation, recorded_at DESC);

-- Function to auto-expire events older than 30 days
-- Run this manually or via cron job in Supabase
CREATE OR REPLACE FUNCTION cleanup_old_events(days_to_keep INT DEFAULT 30)
RETURNS TABLE(deleted_count INT) AS $$
DECLARE
  delete_count INT;
BEGIN
  DELETE FROM bot_events
  WHERE ts < NOW() - INTERVAL '1 day' * days_to_keep;
  
  GET DIAGNOSTICS delete_count = ROW_COUNT;
  
  RETURN QUERY SELECT delete_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to log bot_events inserts
CREATE OR REPLACE FUNCTION log_bot_events_insert()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO bot_audit_log (table_name, operation, device_id, changes)
  VALUES ('bot_events', 'INSERT', NEW.device_id, to_jsonb(NEW));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER bot_events_insert_trigger
AFTER INSERT ON bot_events
FOR EACH ROW
EXECUTE FUNCTION log_bot_events_insert();

-- Trigger to log bot_health updates
CREATE OR REPLACE FUNCTION log_bot_health_update()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO bot_audit_log (table_name, operation, device_id, changes)
  VALUES ('bot_health', 'UPDATE', NEW.device_id, 
          jsonb_build_object('old', to_jsonb(OLD), 'new', to_jsonb(NEW)));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER bot_health_update_trigger
AFTER UPDATE ON bot_health
FOR EACH ROW
EXECUTE FUNCTION log_bot_health_update();
