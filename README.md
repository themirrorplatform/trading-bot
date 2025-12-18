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
# Trading Bot V2

Production-focused Python trading bot with V2 engines (28 signals, sigmoid beliefs, EUC scoring, capital tiers) and SIM + LIVE adapters.

## Prerequisites
- Windows + Python 3.13 (virtualenv recommended)
- SQLite for event store (bundled)
- tzdata (installed) for ZoneInfo("America/New_York")
- Optional for LIVE: websockets (installed via requirements)

## Setup
```powershell
# Create venv
python -m venv src/trading_bot/.venv

# Activate venv
& src/trading_bot/.venv/Scripts/Activate.ps1

# Install packages
pip install -r requirements.txt
```

## Quick Start (SIM)
```powershell
# Ensure package imports work
$env:PYTHONPATH="C:/Users/ilyad/OneDrive/Desktop/trading-bot-v1/trading-bot-v1/src"

# Run a single bar through the pipeline (SIM adapter)
python -m trading_bot.cli run-once --bar-json C:/Users/ilyad/OneDrive/Desktop/trading-bot-v1/trading-bot-v1/src/trading_bot/state/tmp_bar.json --db C:/Users/ilyad/OneDrive/Desktop/trading-bot-v1/trading-bot-v1/data/events.sqlite --adapter tradovate --fill-mode IMMEDIATE
```

## Quick Start (LIVE)
```powershell
# Optional: install websockets if not already installed
pip install websockets

# Run a single bar with LIVE adapter (polling fallback if WS unavailable)
python -m trading_bot.cli run-once --bar-json C:/Users/ilyad/OneDrive/Desktop/trading-bot-v1/trading-bot-v1/src/trading_bot/state/tmp_bar.json --db C:/Users/ilyad/OneDrive/Desktop/trading-bot-v1/trading-bot-v1/data/events.sqlite --adapter tradovate --fill-mode IMMEDIATE --live --instrument MES --account-id <YOUR_ACCOUNT_ID> --access-token <YOUR_TOKEN> --ws-url wss://<your-ws-endpoint>
```

## Notes
- SIM supports fill_mode: IMMEDIATE, DELAYED, PARTIAL, TIMEOUT.
- LIVE adapter is fail-soft: uses HTTP polling if websocket not available.
- Runner handles reconciliation and TTL; adapter enforces kill-switch on heartbeat staleness.

## Testing
```powershell
# Run the V2 integration test
$env:PYTHONPATH="C:/Users/ilyad/OneDrive/Desktop/trading-bot-v1/trading-bot-v1/src"
python -m pytest tests/test_runner_v2_integration.py -q
```

## Troubleshooting
- If ModuleNotFoundError: trading_bot, set PYTHONPATH to the src folder as shown above.
- If ZoneInfoNotFoundError('America/New_York'), ensure tzdata is installed in the venv.
