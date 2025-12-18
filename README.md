# Trading Bot v1 (MES Survival)

Minimal, contract-aligned trading system with:
- Signals (VWAP, ATR via Wilder, session phases)
- Decision engine (constitution-first gating, strategy templates)
- Simulated execution adapter
- Event logging (SQLite append-only)
- CLI for init, seeding, single-run, and replay

## Quick Start (Windows PowerShell)

1) Activate venv

```powershell
& .\src\trading_bot\.venv\Scripts\Activate.ps1
```

2) Run tests

```powershell
python -m pytest -q
```

3) Initialize the event DB

```powershell
python -m trading_bot.cli init-db --db data/events.sqlite --schema src/trading_bot/log/schema.sql
```

4) Seed demo bars

```powershell
python -m trading_bot.cli seed-demo-bars --db data/events.sqlite --stream MES_RTH_DEMO --start-iso 2025-12-18T09:31:00-05:00 --count 60
```

5) Replay seeded stream through the full pipeline

```powershell
python -m trading_bot.cli replay-stream --db data/events.sqlite --stream MES_RTH_DEMO --contracts src/trading_bot/contracts
```

6) Replay from JSON bars (sample provided)

```powershell
python -m trading_bot.cli replay-json --bars samples/bars.json --db data/events.sqlite --stream MES_RTH --contracts src/trading_bot/contracts
```

Phase-specific samples:

```powershell
# Opening (crosses 09:30–09:35 no-trade window)
python -m trading_bot.cli replay-json --bars samples/bars_opening.json --db data/events.sqlite --stream MES_RTH

# Mid-morning (tradable window)
python -m trading_bot.cli replay-json --bars samples/bars_mid_morning.json --db data/events.sqlite --stream MES_RTH

# Lunch (observe-only period)
python -m trading_bot.cli replay-json --bars samples/bars_lunch.json --db data/events.sqlite --stream MES_RTH

# Afternoon
python -m trading_bot.cli replay-json --bars samples/bars_afternoon.json --db data/events.sqlite --stream MES_RTH

# Close
python -m trading_bot.cli replay-json --bars samples/bars_close.json --db data/events.sqlite --stream MES_RTH
```

7) Single-bar decision run

```powershell
python -m trading_bot.cli run-once --bar-json samples/bars.json --db data/events.sqlite
```

## Architecture

- Signals: `SignalEngine` computes session phase, VWAP (typical price, RTH reset at 09:30 ET), True Range, and ATR(14/30) via Wilder smoothing.
- Decision: `DecisionEngine` enforces hierarchy — Kill Switch → Constitution → DVS/EQS → Session → Frequency/Position → Drawdown → Template → Friction.
- Strategy Template: `F1_MEAN_REVERSION` requires mid-morning phase, price < VWAP by −0.15%, ATR norm in [0.40%, 0.75%], spread ≤ 2 ticks, DVS/EQS thresholds, and no existing position.
- Execution: `TradovateAdapter` (SIMULATED v1) immediately fills and tracks positions; live mode deferred.
- Events: `EventStore` (SQLite) stores `BAR_1M`, decisions, and order events.

## Reproducibility

`BotRunner` derives a deterministic `config_hash` from loaded contracts and signal params to fingerprint outputs across runs.

## Contracts

See `src/trading_bot/contracts/` for `constitution.yaml`, `session.yaml`, `strategy_templates.yaml`, and `risk_model.yaml`.

## Notes

- Timezone: America/New_York (ET) for all session logic.
- Fail-closed: Missing required signals (VWAP, ATR, spread) block trades with explicit reason codes.
- Tests: Decision suite aligns with contract thresholds and reason enums.
# trading-bot-v1

Drop this folder into VS Code and start building **one component at a time**.

## What you get

- A complete repo skeleton with canonical contracts (YAML)
- Component 1 implemented: **Event Log + Replay Harness**
- Stubs for all remaining components with clear module boundaries
- Tests that prove replay determinism (foundation for safe evolution)

## Run tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest -q
```

## Where to start coding next

- `src/engines/signals.py` (Component 2)
- `src/engines/belief.py`  (Component 3)

Contracts live in `contracts/`.
