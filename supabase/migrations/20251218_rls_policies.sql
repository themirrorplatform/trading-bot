-- RLS Policies for Supabase Phase 2
-- Enables secure read-only access for anon users
-- Service role writes via Edge Functions

-- Enable RLS on all tables
ALTER TABLE bot_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_latest_snapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_health ENABLE ROW LEVEL SECURITY;

-- =======================
-- bot_devices policies
-- =======================

-- Anon can read all devices (needed for device listing)
CREATE POLICY "Anon read all devices"
ON bot_devices FOR SELECT
USING (auth.role() = 'anon_user' OR auth.role() = 'authenticated');

-- Service role can do everything
CREATE POLICY "Service role full access"
ON bot_devices FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

-- =======================
-- bot_events policies
-- =======================

-- Anon can read bot_events (READ-ONLY)
CREATE POLICY "Anon read bot_events"
ON bot_events FOR SELECT
USING (auth.role() = 'anon_user' OR auth.role() = 'authenticated');

-- Service role can insert (from publisher), delete old records
CREATE POLICY "Service role manage events"
ON bot_events FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

-- =======================
-- bot_latest_snapshot policies
-- =======================

-- Anon can read snapshots
CREATE POLICY "Anon read latest snapshot"
ON bot_latest_snapshot FOR SELECT
USING (auth.role() = 'anon_user' OR auth.role() = 'authenticated');

-- Service role can do everything
CREATE POLICY "Service role manage snapshot"
ON bot_latest_snapshot FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

-- =======================
-- bot_health policies
-- =======================

-- Anon can read health
CREATE POLICY "Anon read bot_health"
ON bot_health FOR SELECT
USING (auth.role() = 'anon_user' OR auth.role() = 'authenticated');

-- Service role can do everything
CREATE POLICY "Service role manage health"
ON bot_health FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');
