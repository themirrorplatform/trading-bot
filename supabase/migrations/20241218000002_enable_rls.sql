-- Enable Row Level Security (RLS) on all bot tables
-- This ensures that only authenticated users can read data

-- Enable RLS on all tables
ALTER TABLE bot_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_latest_snapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_health ENABLE ROW LEVEL SECURITY;

-- Policy: Allow authenticated users to SELECT from bot_events
CREATE POLICY "Authenticated users can read bot_events"
  ON bot_events
  FOR SELECT
  TO authenticated
  USING (true);

-- Policy: Allow authenticated users to SELECT from bot_latest_snapshot
CREATE POLICY "Authenticated users can read bot_latest_snapshot"
  ON bot_latest_snapshot
  FOR SELECT
  TO authenticated
  USING (true);

-- Policy: Allow authenticated users to SELECT from bot_health
CREATE POLICY "Authenticated users can read bot_health"
  ON bot_health
  FOR SELECT
  TO authenticated
  USING (true);

-- Policy: Allow service role to INSERT/UPDATE/DELETE on bot_events
CREATE POLICY "Service role can write bot_events"
  ON bot_events
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Policy: Allow service role to INSERT/UPDATE/DELETE on bot_latest_snapshot
CREATE POLICY "Service role can write bot_latest_snapshot"
  ON bot_latest_snapshot
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Policy: Allow service role to INSERT/UPDATE/DELETE on bot_health
CREATE POLICY "Service role can write bot_health"
  ON bot_health
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Add comments
COMMENT ON POLICY "Authenticated users can read bot_events" ON bot_events IS 'UI users can read events via anon key + JWT';
COMMENT ON POLICY "Service role can write bot_events" ON bot_events IS 'Edge Function can write events via service role key';
