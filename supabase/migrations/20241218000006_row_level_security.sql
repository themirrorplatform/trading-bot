-- Row Level Security Policies
-- Secure access to trading data

-- Enable RLS on all tables
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE decision_journal ENABLE ROW LEVEL SECURITY;

-- For now, allow authenticated users full access
-- In production, you'd want user-specific access control

-- Events: Read-only for authenticated users, insert for service role
CREATE POLICY "Allow authenticated read events"
ON events FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Allow service role insert events"
ON events FOR INSERT
TO service_role
WITH CHECK (true);

-- Trades: Full access for authenticated users
CREATE POLICY "Allow authenticated access trades"
ON trades FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- Daily Summary: Full access for authenticated users
CREATE POLICY "Allow authenticated access daily_summary"
ON daily_summary FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- Decision Journal: Read for authenticated, insert for service role
CREATE POLICY "Allow authenticated read journal"
ON decision_journal FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Allow service role insert journal"
ON decision_journal FOR INSERT
TO service_role
WITH CHECK (true);

-- Anonymous access for dashboard (read-only)
-- Remove these in production if you want auth-only access
CREATE POLICY "Allow anon read events"
ON events FOR SELECT
TO anon
USING (true);

CREATE POLICY "Allow anon read trades"
ON trades FOR SELECT
TO anon
USING (true);

CREATE POLICY "Allow anon read daily_summary"
ON daily_summary FOR SELECT
TO anon
USING (true);

CREATE POLICY "Allow anon read journal"
ON decision_journal FOR SELECT
TO anon
USING (true);

COMMENT ON POLICY "Allow authenticated read events" ON events IS 'Authenticated users can read all events';
COMMENT ON POLICY "Allow service role insert events" ON events IS 'Only service role (bot backend) can insert events';
