-- Trading Bot Tables for Phase-2 Monitoring
-- This migration creates the three core tables for bot monitoring

-- Bot Events Table (append-only event log)
CREATE TABLE IF NOT EXISTS bot_events (
  id TEXT PRIMARY KEY,
  device_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for efficient device_id filtering
CREATE INDEX IF NOT EXISTS idx_bot_events_device_id ON bot_events(device_id);
CREATE INDEX IF NOT EXISTS idx_bot_events_timestamp ON bot_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_bot_events_device_timestamp ON bot_events(device_id, timestamp DESC);

-- Bot Latest Snapshot Table (one row per device, updated on each state change)
CREATE TABLE IF NOT EXISTS bot_latest_snapshot (
  device_id TEXT PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  equity NUMERIC NOT NULL,
  position INTEGER NOT NULL DEFAULT 0,
  unrealized_pnl NUMERIC NOT NULL DEFAULT 0,
  realized_pnl NUMERIC NOT NULL DEFAULT 0,
  daily_pnl NUMERIC NOT NULL DEFAULT 0,
  signals JSONB,
  beliefs JSONB,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bot Health Table (one row per device, updated on heartbeat)
CREATE TABLE IF NOT EXISTS bot_health (
  device_id TEXT PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('healthy', 'degraded', 'down')),
  dvs NUMERIC NOT NULL CHECK (dvs >= 0 AND dvs <= 1),
  eqs NUMERIC NOT NULL CHECK (eqs >= 0 AND eqs <= 1),
  kill_switch_active BOOLEAN NOT NULL DEFAULT FALSE,
  last_heartbeat TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers to auto-update updated_at
CREATE TRIGGER update_bot_latest_snapshot_updated_at
  BEFORE UPDATE ON bot_latest_snapshot
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bot_health_updated_at
  BEFORE UPDATE ON bot_health
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE bot_events IS 'Append-only log of all bot events (decisions, orders, fills)';
COMMENT ON TABLE bot_latest_snapshot IS 'Current state snapshot for each bot (equity, position, P&L)';
COMMENT ON TABLE bot_health IS 'Health monitoring data for each bot (DVS, EQS, kill switch)';
