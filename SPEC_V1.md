# SPEC_V1 — Survival-First MES Trading System

This repository is a **build-ready scaffold** for a survival-first trading system:
> **a survival machine that occasionally expresses asymmetric beliefs through trades**

## Authority Order (highest → lowest)

1. Kill switch
2. Constitution (invariants)
3. Quality gates (DVS/EQS)
4. Regime gates
5. Capital gates
6. Belief + stability
7. Friction gate
8. Template execution

A trade happens only when **all layers** say YES.

## What is implemented in v1 scaffold

### Component 1 (implemented): Event Log + Replay Harness
- Append-only SQLite event store
- Idempotent inserts by deterministic `event_id`
- Read stream ordered by timestamp
- Replay harness to prove determinism before trading

### Components 2–7 (planned in folder, stubbed)
- Signal engine (28 signals, normalized)
- Belief engine (constraints, decay, stability)
- Decision engine (observation mode)
- Simulated execution (pessimistic friction)
- Attribution engine (A0–A9, ordered first-match)
- Tradovate adapter (interface only; v1 uses simulation)

## Contracts (canonical law)
All behavior is governed by YAML contracts in `contracts/`.
Implementation **must not invent behavior** not covered by these contracts.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

pytest -q
```

## Build sequence (one-by-one)

1. Event Log + Replay Harness ✅
2. Signal Engine
3. Belief Engine
4. Decision Engine (observe only)
5. Simulated fills
6. Attribution engine
7. Tradovate adapter (micro-risk live)
