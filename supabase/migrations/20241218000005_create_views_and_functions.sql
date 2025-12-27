-- Views and Functions for Dashboard Queries

-- Recent decisions view (last 100)
CREATE OR REPLACE VIEW recent_decisions AS
SELECT
    e.id,
    e.stream_id,
    e.timestamp,
    e.payload->>'action' as action,
    e.payload->>'reason' as reason,
    e.payload->'metadata'->>'template_id' as template_id,
    (e.payload->'metadata'->>'euc_score')::decimal as euc_score,
    e.payload->'metadata'->>'tier' as tier,
    e.config_hash
FROM events e
WHERE e.event_type = 'DECISION_1M'
ORDER BY e.timestamp DESC
LIMIT 100;

-- Today's trades view
CREATE OR REPLACE VIEW today_trades AS
SELECT
    t.*,
    CASE
        WHEN t.pnl_usd > 0 THEN 'WIN'
        WHEN t.pnl_usd < 0 THEN 'LOSS'
        ELSE 'SCRATCH'
    END as outcome
FROM trades t
WHERE t.entry_time::date = CURRENT_DATE
ORDER BY t.entry_time DESC;

-- Performance by template view
CREATE OR REPLACE VIEW template_performance AS
SELECT
    template_id,
    COUNT(*) as trade_count,
    SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN pnl_usd < 0 THEN 1 ELSE 0 END) as losses,
    ROUND(SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END)::decimal / NULLIF(COUNT(*), 0) * 100, 1) as win_rate_pct,
    ROUND(SUM(COALESCE(pnl_usd, 0))::decimal, 2) as total_pnl,
    ROUND(AVG(COALESCE(pnl_usd, 0))::decimal, 2) as avg_pnl,
    ROUND(AVG(euc_score)::decimal, 4) as avg_euc_score
FROM trades
WHERE exit_time IS NOT NULL
GROUP BY template_id
ORDER BY total_pnl DESC;

-- Function to calculate running equity curve
CREATE OR REPLACE FUNCTION get_equity_curve(
    p_stream_id TEXT,
    p_start_date DATE DEFAULT CURRENT_DATE - INTERVAL '30 days',
    p_end_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    date DATE,
    equity DECIMAL(12, 2),
    daily_pnl DECIMAL(10, 2),
    cumulative_pnl DECIMAL(10, 2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ds.date,
        ds.ending_equity as equity,
        ds.pnl_usd as daily_pnl,
        SUM(ds.pnl_usd) OVER (ORDER BY ds.date) as cumulative_pnl
    FROM daily_summary ds
    WHERE ds.stream_id = p_stream_id
      AND ds.date BETWEEN p_start_date AND p_end_date
    ORDER BY ds.date;
END;
$$ LANGUAGE plpgsql;

-- Function to get latest bot state
CREATE OR REPLACE FUNCTION get_bot_state(p_stream_id TEXT)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'last_decision', (
            SELECT payload
            FROM events
            WHERE stream_id = p_stream_id AND event_type = 'DECISION_1M'
            ORDER BY timestamp DESC LIMIT 1
        ),
        'last_beliefs', (
            SELECT payload
            FROM events
            WHERE stream_id = p_stream_id AND event_type = 'BELIEFS_1M'
            ORDER BY timestamp DESC LIMIT 1
        ),
        'last_bar', (
            SELECT payload
            FROM events
            WHERE stream_id = p_stream_id AND event_type = 'BAR_1M'
            ORDER BY timestamp DESC LIMIT 1
        ),
        'open_position', (
            SELECT COALESCE(
                (SELECT payload->>'position'
                 FROM events
                 WHERE stream_id = p_stream_id AND event_type = 'SYSTEM_EVENT'
                 ORDER BY timestamp DESC LIMIT 1
                )::integer, 0
            )
        )
    ) INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Real-time subscription helper
-- Enable realtime for events table
ALTER PUBLICATION supabase_realtime ADD TABLE events;

COMMENT ON VIEW recent_decisions IS 'Last 100 trading decisions for dashboard';
COMMENT ON VIEW today_trades IS 'All trades from today with outcome';
COMMENT ON VIEW template_performance IS 'Aggregated performance by template (K1-K4)';
