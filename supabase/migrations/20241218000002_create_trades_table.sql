-- Trades Table
-- Denormalized view of completed trades for fast querying

CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stream_id TEXT NOT NULL,

    -- Entry details
    entry_time TIMESTAMPTZ NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT')),
    contracts INTEGER NOT NULL DEFAULT 1,
    entry_price DECIMAL(10, 2) NOT NULL,
    template_id TEXT NOT NULL,
    euc_score DECIMAL(5, 4),
    tier TEXT CHECK (tier IN ('S', 'A', 'B')),

    -- Exit details (nullable until trade closed)
    exit_time TIMESTAMPTZ,
    exit_price DECIMAL(10, 2),
    exit_reason TEXT,

    -- P&L
    pnl_ticks INTEGER,
    pnl_usd DECIMAL(10, 2),

    -- Quality metrics
    slippage_ticks INTEGER,
    dvs_at_entry DECIMAL(3, 2),
    eqs_at_entry DECIMAL(3, 2),

    -- Attribution
    attribution_code TEXT,
    edge_score DECIMAL(3, 2),
    luck_score DECIMAL(3, 2),
    execution_score DECIMAL(3, 2),
    learning_weight DECIMAL(3, 2),

    -- Metadata
    config_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_trades_stream_id ON trades(stream_id);
CREATE INDEX idx_trades_entry_time ON trades(entry_time DESC);
CREATE INDEX idx_trades_template_id ON trades(template_id);
CREATE INDEX idx_trades_attribution ON trades(attribution_code);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_trades_updated_at
    BEFORE UPDATE ON trades
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE trades IS 'Denormalized trade records for dashboard queries';
COMMENT ON COLUMN trades.template_id IS 'K1-K4 template that triggered the trade';
COMMENT ON COLUMN trades.euc_score IS 'Edge-Uncertainty-Cost score at entry';
COMMENT ON COLUMN trades.learning_weight IS '(1 - luck_score) * execution_score';
