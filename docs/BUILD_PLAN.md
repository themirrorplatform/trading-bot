# Build Plan (one component at a time)

This repo is intentionally **fail-closed**: missing definitions are treated as errors, not guesses.

## Component 1 — Event Log + Replay Harness (DONE in scaffold)

**Goal:** Prove determinism and preserve truth.
- SQLite append-only event store (`src/trading_bot/log/event_store.py`)
- Deterministic event_id (`src/trading_bot/core/types.py`)
- Replay harness (`src/trading_bot/log/replay.py`)
- Minimal tests

### Acceptance criteria
- Idempotent inserts
- Stream replay produces stable output fingerprint

## Component 2 — Signal Engine (NEXT)

**Input:** BAR_1M events (OHLCV), rolling stats state
**Output:** SIGNALS_1M events with:
- 28 signals in [-1, +1]
- reliability in [0, 1]
- derived stats used (ATR, VWAP, etc.)

**Must implement from:** `contracts/data_contract.yaml`, `contracts/market_instrument.yaml`

## Component 3 — Belief Engine

**Input:** SIGNALS_1M + previous beliefs
**Output:** BELIEFS_1M
- per-constraint update, decay λ, tier normalization, stability metric

**Must implement from:** `contracts/learning_protocol.yaml`

## Component 4 — Decision Engine (Observation Mode)

**Input:** BELIEFS_1M + gates + state
**Output:** DECISION_1M
- always NO_TRADE until simulator wired
- must emit `no_trade_reason` consistently

**Must implement from:** `contracts/constitution.yaml`, `contracts/strategy_templates.yaml`

## Component 5 — Simulator

**Input:** ORDER_INTENT + market state
**Output:** FILL_EVENT + POSITION_SNAPSHOT

**Must implement from:** `contracts/execution_contract.yaml`

## Component 6 — Attribution Engine

**Input:** Completed trade record + lookforward windows
**Output:** Attribution A0–A9 + process/outcome scores

**Must implement from:** `contracts/learning_protocol.yaml`

## Component 7 — Tradovate Adapter

**Goal:** Replace simulator with real execution without changing the higher layers.
**Must obey:** `contracts/state_contract.yaml`, kill-switch rules.

---
