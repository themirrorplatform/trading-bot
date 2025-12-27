# MES Trading Bot (IBKR Production-Ready)

This workspace implements the **locked specification** for a survival-first MES trading bot per the 9 locked specification documents. All core systems are scaffolded and tested: broker gateway, constitutional filter, canonical events, append-only logging, observation mode, and LIVE `ib_insync` integration.

## Architecture Overview

- **Broker Gateway**: `broker_gateway/ibkr/` (connection, market data, execution, account, session, constitutional filter)
- **Adapter**: `adapters/ibkr_adapter.py` integrates gateway with runner (OBSERVE | LIVE)
- **Canonical Events**: `core/events.py` (Pydantic schemas per Section 12)
- **Constitution**: `contracts/constitution.yaml` ($15 cap, $1,500 min capital, tier gates)
- **Event Store**: SQLite WAL, append-only log in `log/event_store.py`

## Quick Start (Observation Mode)

### 1. Initialize DB

```powershell
$env:PYTHONPATH = "$(Resolve-Path ./src)"
./src/trading_bot/.venv/Scripts/python.exe ./src/trading_bot/cli.py init-db --db ./data/events.sqlite --schema ./src/trading_bot/log/schema.sql
```

### 2. Run Single Bar (IBKR Adapter, OBSERVE)

```powershell
$env:PYTHONPATH = "$(Resolve-Path ./src)"
./src/trading_bot/.venv/Scripts/python.exe ./src/trading_bot/cli.py run-once --bar-json ./data/test_bar.json --db ./data/events.sqlite --adapter ibkr
```

### 3. Inspect Events

```powershell
$env:PYTHONPATH = "$(Resolve-Path ./src)"
./src/trading_bot/.venv/Scripts/python.exe ./src/trading_bot/cli.py report --db ./data/events.sqlite --stream MES_RTH
```

## Test Harnesses

All tests respect PYTHONPATH convention:

```powershell
$env:PYTHONPATH = "C:/Users/ilyad/OneDrive/Desktop/trading-bot-v1/trading-bot-v1/src"
```

### Gate Tests (DVS/EQS/Session)

```powershell
./src/trading_bot/.venv/Scripts/python.exe ./src/trading_bot/tools/gate_tests.py
```

Expected: DVS_TOO_LOW and EQS_TOO_LOW rejections.

### Determinism Test

```powershell
./src/trading_bot/.venv/Scripts/python.exe ./src/trading_bot/tools/determinism_test.py
```

Expected: `"equal": true` for isolated runner instances.

### Regime-Switch Test

```powershell
./src/trading_bot/.venv/Scripts/python.exe ./src/trading_bot/tools/regime_switch_test.py | Out-String -Stream | Select-Object -First 50
```

Expected: Beliefs adapt across chop → trend → chop transitions.

### Friction Torture Test

```powershell
./src/trading_bot/.venv/Scripts/python.exe ./src/trading_bot/tools/friction_torture_test.py
```

Expected: High friction scenario blocks trades.

### Shadow Parameter Validation

```powershell
./src/trading_bot/.venv/Scripts/python.exe ./src/trading_bot/tools/shadow_test.py
```

Expected: Promotion gating based on 30+ samples, 5% outperformance.

## LIVE Mode (ib_insync)

To enable LIVE submission and real-time market data:

1. Install `ib_insync` (optional dependency):

```powershell
./src/trading_bot/.venv/Scripts/pip.exe install ib-insync
```

2. Start TWS or IB Gateway (Paper: port 7497, LIVE: port 7496)

3. Update `runtime.yaml`:

```yaml
adapter: ibkr
adapter_kwargs:
  mode: LIVE  # Switch from OBSERVE
  host: 127.0.0.1
  port: 7497  # Paper
```

4. Market data streaming:

```python
from trading_bot.broker_gateway.ibkr.market_data_adapter import MarketDataAdapter

def on_bar(bar):
    # Process bar with runner
    pass

adapter = MarketDataAdapter(on_bar_closed=on_bar)
adapter.subscribe_mes_bars()
```

## Constitution Highlights

- **Max risk per trade**: $15 (12 ticks @ $1.25/tick)
- **Min capital**: $1,500 (IBKR margin requirement)
- **Daily loss cap**: $30
- **Max consecutive losses**: 2 (then pause until next session)
- **Max trades/day**: 2
- **Flatten deadline**: 15:55 ET (no overnight)

## What's Implemented

✅ Constitutional filter with DVS/EQS/session gates  
✅ IBKR adapter (OBSERVE | LIVE via `ib_insync`)  
✅ Real-time market data hook (reqRealTimeBars)  
✅ Bracket order submission (entry + stop + target)  
✅ Position tracking and reconciliation  
✅ Append-only event log (replay-ready)  
✅ Gate tests, determinism, regime-switch, friction torture  
✅ Shadow parameter validation scaffold  

## Next Steps for Production

- Run observation mode for 20+ days; ensure process score > 0.90 and no A9 (mystery) losses.
- Implement DVS penalty calculation in market_data_adapter (bar lag, gaps, outliers).
- Expand event queries and dashboards in `log/` for real-time monitoring.
- Add FastAPI status endpoint for remote observability.
- Implement attribution engine (A0-A9) classification per Section 10.
- Wire evolution engine for shadow parameter updates per Section 11.

---

**Locked Specification Documents**  
1. Constitution and Invariants (Section 1)  
2. Market and Instrument Contract (Section 2)  
3. Data Contract (Sections 5-6)  
4. Execution Contract (Section 13)  
5. Strategy Definition (Sections 7-8)  
6. Risk Model (Section 3)  
7. Evaluation and Learning Protocol (Sections 10-11)  
8. Observability (Section 14)  
9. IBKR Integration (Section 13)
