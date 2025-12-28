# IBKR Paper Trading Verification Report

**Date:** December 28, 2025
**Time:** 1:39 PM EST (Sunday)
**Next Market Open:** Sunday 6:00 PM ET (Futures)
**Purpose:** Verify bot is ready for IBKR paper trading and UI is collecting evolution data

---

## Executive Summary

| Component | Status | Action Required |
|-----------|--------|-----------------|
| IBKR Gateway/TWS | **NOT RUNNING** | Start IB Gateway with paper trading |
| Trading Bot Process | **NOT RUNNING** | Start bot with IBKR adapter |
| IB API Package | **NOT INSTALLED** | Install `ib_insync` |
| Runtime Config | **WRONG ADAPTER** | Switch from `tradovate` to `ibkr` |
| Publisher | **NOT CONFIGURED** | Create `publisher/config.json` |
| UI Data Source | **MOCK MODE** | Switch to `supabase` for live data |
| Last Event | **10 DAYS OLD** | Dec 18, 2025 - bot hasn't run since |

---

## Detailed Findings

### 1. IBKR Gateway Connection

**Status:** NOT CONNECTED

- Port 7497 (paper trading) is NOT listening
- Port 7496 (live trading) is NOT listening
- No IB Gateway or TWS process detected
- `ib_insync` package is NOT installed

**Required Actions:**
```bash
# 1. Install IB API package
pip install ib_insync

# 2. Start IB Gateway (or TWS)
# - Use paper trading mode
# - Port 7497 is the default paper trading port
# - Enable API connections in Gateway settings
```

### 2. Runtime Configuration

**Current Config (src/trading_bot/runtime.yaml):**
```yaml
adapter: tradovate  # WRONG - should be 'ibkr'
fill_mode: IMMEDIATE
adapter_kwargs:
  base_url: http://127.0.0.1:8123
  auth_token: changeme
```

**Required Change:**
```yaml
adapter: ibkr
adapter_kwargs:
  host: 127.0.0.1
  port: 7497  # Paper trading
  client_id: 1
  mode: OBSERVE  # or LIVE when ready to execute
```

### 3. Database Status

**Local SQLite:** `data/events.sqlite`
- Total Events: 153
- Last Event: December 18, 2025 (10 days ago!)
- Event Types Recorded:
  - `DECISION_1M` - Trade decisions
  - `DECISION_RECORD` - Decision journal entries
  - `BELIEFS_1M` - Belief state
  - `RECONCILIATION` - Position reconciliation

**Last Event Details:**
```
Timestamp: 2025-12-18T10:15:00-05:00
Type: DECISION_1M
Action: NO_TRADE
Reason: BELIEF_TOO_LOW
```

### 4. Publisher Status

**Status:** NOT CONFIGURED

- Missing `publisher/config.json` - publisher cannot sync events to Supabase
- No `.publisher_state.json` - no sync state saved

**Required Config (publisher/config.json):**
```json
{
  "device_id": "bot-01",
  "mirror_url": "https://hhyilmbejidzriljesph.functions.supabase.co/mirror-events",
  "secret": "<your-shared-secret>",
  "batch_size": 200,
  "poll_ms": 1000
}
```

### 5. UI Data Collection

**Local UI Config (ui/.env):**
```
VITE_DATA_SOURCE=mock  # Using mock data, NOT live!
VITE_SUPABASE_URL=https://hhyilmbejidzriljesph.supabase.co
VITE_STREAM_ID=MES_RTH
```

**Netlify Deploy Config (netlify.toml):**
```
VITE_DATA_SOURCE=supabase  # Correct for production
```

**Issue:** Local development uses mock data, so the UI won't show real trading data during local testing.

**Required Change for Local Live Testing:**
```bash
# In ui/.env, change:
VITE_DATA_SOURCE=supabase
```

### 6. Evolution Engine (Learning)

**Status:** READY (code exists, needs trades to learn from)

The evolution engine (`src/trading_bot/engines/evolution.py`) is properly implemented:
- Learns from attributed trades (A0-A9 codes)
- Adjusts signal weights, belief thresholds, decay rates
- Updates template-specific parameters
- Runs on weekly cadence with constitutional bounds

**To run evolution learning:**
```bash
python -m trading_bot.cli evolve --dry-run  # Preview changes
python -m trading_bot.cli evolve --force    # Apply changes
```

---

## Startup Checklist for Tonight's Market Open

### Pre-Market Setup (Before 6 PM ET)

1. **Install Dependencies**
   ```bash
   pip install ib_insync
   ```

2. **Start IB Gateway/TWS**
   - Launch IB Gateway (preferred) or TWS
   - Select Paper Trading account
   - Enable API connections:
     - Settings > API > Enable ActiveX and Socket Clients
     - Socket Port: 7497
     - Allow connections from localhost only: checked

3. **Update Runtime Config**
   Edit `src/trading_bot/runtime.yaml`:
   ```yaml
   adapter: ibkr
   adapter_kwargs:
     host: 127.0.0.1
     port: 7497
     client_id: 1
     mode: OBSERVE
   ```

4. **Test IBKR Connection**
   ```bash
   python src/trading_bot/tools/ibkr_quick_tests.py connect
   # Should show: {'Connected': True, 'Accounts': ['DU...']}
   ```

5. **Configure Publisher**
   Create `publisher/config.json` with your Supabase edge function URL and secret.

6. **Start Bot**
   ```bash
   # Option 1: Run once to test
   python -m trading_bot.cli run-once --bar-json samples/bars.json --adapter ibkr

   # Option 2: Live trading loop (when ready)
   python -m trading_bot.cli live --symbol MESH5 --environment demo
   ```

7. **Start Publisher**
   ```bash
   python publisher/publisher.py
   ```

8. **Verify UI Shows Data**
   - Local: Set `VITE_DATA_SOURCE=supabase` in `ui/.env`
   - Run `npm run dev` in `ui/` directory
   - Check dashboard for live events

---

## IBKR Paper Trading Ports Reference

| Port | Mode | Usage |
|------|------|-------|
| 7497 | Paper | IB Gateway/TWS paper trading API |
| 7496 | Live | IB Gateway/TWS live trading API |
| 4002 | Paper | IB Gateway (newer default for paper) |
| 4001 | Live | IB Gateway (newer default for live) |

---

## Safety Checks

The IBKR adapter has multiple safety layers:

1. **Kill Switch**: `adapter.set_kill_switch(True)` - flattens all positions
2. **Execution Gate**: `execution_enabled` must be True
3. **DVS Gate**: Data Validity Score must be >= 0.80
4. **EQS Gate**: Execution Quality Score must be >= 0.75
5. **Session Gate**: Market must be open
6. **Account Gate**: Equity must be positive
7. **Constitutional Filter**: Orders validated against rules

**Current Mode:** `OBSERVE` (default) - will NOT execute real orders

---

## File Locations

| Component | Path |
|-----------|------|
| IBKR Adapter | `src/trading_bot/adapters/ibkr_adapter.py` |
| Runtime Config | `src/trading_bot/runtime.yaml` |
| Contracts | `src/trading_bot/contracts/*.yaml` |
| Event Store | `data/events.sqlite` |
| Publisher | `publisher/publisher.py` |
| UI Config | `ui/.env` |
| IBKR Tests | `src/trading_bot/tools/ibkr_quick_tests.py` |
| CLI | `src/trading_bot/cli.py` |

---

## Next Steps

1. [ ] Install `ib_insync` package
2. [ ] Start IB Gateway with paper trading enabled
3. [ ] Update runtime.yaml to use IBKR adapter
4. [ ] Test connection with `ibkr_quick_tests.py connect`
5. [ ] Configure publisher with Supabase credentials
6. [ ] Start bot process
7. [ ] Start publisher process
8. [ ] Verify events appearing in Supabase
9. [ ] Check UI dashboard shows live data
10. [ ] Monitor first trading decisions at market open

---

*Report generated by verification script on 2025-12-28*
