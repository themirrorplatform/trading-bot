-- Trading Bot Events Table
-- Mirrors the Python SQLite event store schema for cloud persistence

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Events table (immutable event log)
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stream_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    config_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint for idempotent inserts
    CONSTRAINT events_unique_entry UNIQUE (stream_id, timestamp, event_type, config_hash)
);

-- Indexes for common queries
CREATE INDEX idx_events_stream_id ON events(stream_id);
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX idx_events_event_type ON events(event_type);
CREATE INDEX idx_events_stream_type_time ON events(stream_id, event_type, timestamp DESC);

-- Event types:
-- BAR_1M: Raw bar data
-- SIGNALS_1M: Computed signals (28 in V2)
-- BELIEFS_1M: Constraint likelihoods
-- DECISION_1M: Trade/no-trade decision
-- ORDER_EVENT: Order placement result
-- FILL_EVENT: Fill confirmation
-- ATTRIBUTION: Trade attribution (A0-A9)
-- SYSTEM_EVENT: Reconciliation, kill switch, etc.
-- DECISION_JOURNAL: Plain English explanations

COMMENT ON TABLE events IS 'Immutable event log for trading bot. Supports deterministic replay.';
COMMENT ON COLUMN events.stream_id IS 'Instrument stream identifier (e.g., MES_RTH)';
COMMENT ON COLUMN events.event_type IS 'Event type code (BAR_1M, DECISION_1M, etc.)';
COMMENT ON COLUMN events.payload IS 'Event-specific JSON payload';
COMMENT ON COLUMN events.config_hash IS 'SHA256 of bot configuration for reproducibility';
