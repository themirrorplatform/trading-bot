-- Daily Summary Table
-- Aggregated daily statistics for performance tracking

CREATE TABLE IF NOT EXISTS daily_summary (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    stream_id TEXT NOT NULL,

    -- Equity tracking
    starting_equity DECIMAL(12, 2) NOT NULL,
    ending_equity DECIMAL(12, 2) NOT NULL,
    high_water_mark DECIMAL(12, 2),

    -- P&L
    pnl_usd DECIMAL(10, 2) NOT NULL DEFAULT 0,
    pnl_pct DECIMAL(6, 4),

    -- Trade stats
    trade_count INTEGER NOT NULL DEFAULT 0,
    win_count INTEGER NOT NULL DEFAULT 0,
    loss_count INTEGER NOT NULL DEFAULT 0,
    scratch_count INTEGER NOT NULL DEFAULT 0,

    -- Win rate and expectancy
    win_rate DECIMAL(5, 4),
    avg_win_usd DECIMAL(10, 2),
    avg_loss_usd DECIMAL(10, 2),
    expectancy_usd DECIMAL(10, 2),
    profit_factor DECIMAL(6, 2),

    -- Risk metrics
    max_drawdown_usd DECIMAL(10, 2),
    max_drawdown_pct DECIMAL(6, 4),
    consecutive_losses INTEGER DEFAULT 0,

    -- Template breakdown (JSON for flexibility)
    template_stats JSONB DEFAULT '{}',
    -- Example: {"K1": {"count": 5, "pnl": 45.00}, "K2": {"count": 2, "pnl": -12.00}}

    -- Session stats
    skip_count INTEGER DEFAULT 0,
    kill_switch_events INTEGER DEFAULT 0,
    reconciliation_errors INTEGER DEFAULT 0,

    -- Quality averages
    avg_dvs DECIMAL(3, 2),
    avg_eqs DECIMAL(3, 2),
    avg_euc_score DECIMAL(5, 4),

    -- Config tracking
    config_hash TEXT NOT NULL,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique per day per stream
    CONSTRAINT daily_summary_unique UNIQUE (date, stream_id, config_hash)
);

-- Indexes
CREATE INDEX idx_daily_summary_date ON daily_summary(date DESC);
CREATE INDEX idx_daily_summary_stream ON daily_summary(stream_id);

-- Trigger for updated_at
CREATE TRIGGER update_daily_summary_updated_at
    BEFORE UPDATE ON daily_summary
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE daily_summary IS 'Daily aggregated trading statistics';
COMMENT ON COLUMN daily_summary.profit_factor IS 'Gross profits / Gross losses';
COMMENT ON COLUMN daily_summary.expectancy_usd IS 'Average P&L per trade';
