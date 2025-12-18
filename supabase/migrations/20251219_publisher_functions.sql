-- Publisher setup migration
-- Manages bot instance registration and publish-subscribe verification

-- Function to register or update bot device
CREATE OR REPLACE FUNCTION register_bot_device(
  device_id TEXT,
  device_name TEXT
) RETURNS BOOLEAN AS $$
BEGIN
  INSERT INTO bot_devices (device_id, name, created_at, last_seen_at)
  VALUES (device_id, device_name, NOW(), NOW())
  ON CONFLICT (device_id) DO UPDATE SET
    last_seen_at = NOW(),
    name = COALESCE(EXCLUDED.name, bot_devices.name);
  RETURN TRUE;
EXCEPTION WHEN OTHERS THEN
  RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to insert bot event
CREATE OR REPLACE FUNCTION insert_bot_event(
  p_device_id TEXT,
  p_seq BIGINT,
  p_event_id TEXT,
  p_ts TIMESTAMPTZ,
  p_type TEXT,
  p_severity TEXT,
  p_symbol TEXT,
  p_session TEXT,
  p_reason_codes TEXT[],
  p_summary TEXT,
  p_payload JSONB
) RETURNS BOOLEAN AS $$
BEGIN
  INSERT INTO bot_events (
    device_id, seq, event_id, ts, type, severity,
    symbol, session, reason_codes, summary, payload
  ) VALUES (
    p_device_id, p_seq, p_event_id, p_ts, p_type, p_severity,
    p_symbol, p_session, p_reason_codes, p_summary, p_payload
  );
  RETURN TRUE;
EXCEPTION WHEN OTHERS THEN
  RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to update bot snapshot
CREATE OR REPLACE FUNCTION update_bot_snapshot(
  p_device_id TEXT,
  p_seq BIGINT,
  p_snapshot JSONB
) RETURNS BOOLEAN AS $$
BEGIN
  INSERT INTO bot_latest_snapshot (device_id, last_seq, snapshot, updated_at)
  VALUES (p_device_id, p_seq, p_snapshot, NOW())
  ON CONFLICT (device_id) DO UPDATE SET
    last_seq = EXCLUDED.last_seq,
    snapshot = EXCLUDED.snapshot,
    updated_at = NOW();
  RETURN TRUE;
EXCEPTION WHEN OTHERS THEN
  RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to update bot health
CREATE OR REPLACE FUNCTION update_bot_health(
  p_device_id TEXT,
  p_mode TEXT,
  p_kill_switch TEXT,
  p_feed_latency_ms INT,
  p_missing_bars INT,
  p_clock_drift_ms INT,
  p_notes TEXT
) RETURNS BOOLEAN AS $$
BEGIN
  INSERT INTO bot_health (
    device_id, mode, kill_switch, feed_latency_ms,
    missing_bars, clock_drift_ms, notes, updated_at
  ) VALUES (
    p_device_id, p_mode, p_kill_switch, p_feed_latency_ms,
    p_missing_bars, p_clock_drift_ms, p_notes, NOW()
  )
  ON CONFLICT (device_id) DO UPDATE SET
    mode = EXCLUDED.mode,
    kill_switch = EXCLUDED.kill_switch,
    feed_latency_ms = EXCLUDED.feed_latency_ms,
    missing_bars = EXCLUDED.missing_bars,
    clock_drift_ms = EXCLUDED.clock_drift_ms,
    notes = EXCLUDED.notes,
    updated_at = NOW();
  RETURN TRUE;
EXCEPTION WHEN OTHERS THEN
  RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant function permissions to service role only
GRANT EXECUTE ON FUNCTION register_bot_device(TEXT, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION insert_bot_event(TEXT, BIGINT, TEXT, TIMESTAMPTZ, TEXT, TEXT, TEXT, TEXT, TEXT[], TEXT, JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION update_bot_snapshot(TEXT, BIGINT, JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION update_bot_health(TEXT, TEXT, TEXT, INT, INT, INT, TEXT) TO service_role;
