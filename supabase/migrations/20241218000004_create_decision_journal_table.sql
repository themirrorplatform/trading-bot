-- Decision Journal Table
-- Human-readable decision explanations for review and learning

CREATE TABLE IF NOT EXISTS decision_journal (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stream_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,

    -- Decision outcome
    action TEXT NOT NULL CHECK (action IN ('ENTER', 'SKIP', 'EXIT')),

    -- Setup scores (constraint likelihoods)
    setup_scores JSONB NOT NULL DEFAULT '{}',
    -- Example: {"F1": 0.72, "F3": 0.45, "F4": 0.38, "F5": 0.55, "F6": 0.82}

    -- EUC score (only for ENTER)
    euc_score DECIMAL(5, 4),

    -- Reason details
    reason_code TEXT,
    reason_details JSONB DEFAULT '{}',

    -- Plain English explanation
    plain_english TEXT NOT NULL,

    -- Context snapshot
    context JSONB NOT NULL DEFAULT '{}',
    -- Example: {"dvs": 0.95, "eqs": 0.88, "session_phase": 2, "spread_ticks": 1}

    -- Linked trade (if ENTER)
    trade_id UUID REFERENCES trades(id),

    -- Config tracking
    config_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_journal_stream_time ON decision_journal(stream_id, timestamp DESC);
CREATE INDEX idx_journal_action ON decision_journal(action);
CREATE INDEX idx_journal_reason ON decision_journal(reason_code);

COMMENT ON TABLE decision_journal IS 'Plain English explanations for every decision';
COMMENT ON COLUMN decision_journal.plain_english IS 'Human-readable explanation of why this decision was made';
