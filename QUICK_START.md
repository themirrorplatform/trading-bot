# Quick Start Guide - Trading Bot v1

## Setup

### 1. Prerequisites
```bash
# Python 3.9+
python --version

# Install IBKR API (if live trading)
pip install ibapi

# Install dependencies
cd src/trading_bot
pip install -r requirements.txt
```

### 2. Configure IBKR
For paper trading:
- Enable "Enable ActiveX and Socket Clients" in TWS settings
- Set API port to 7497 (paper) or 7496 (live)
- Login to TWS

### 3. Set Environment
```bash
cd C:\Users\ilyad\OneDrive\Desktop\trading-bot-v1\trading-bot-v1\src\trading_bot
set PYTHONPATH=.
```

---

## Run Modes

### E2E Demo (Simulated, No IBKR Required)
**Perfect for initial testing and understanding the bot.**

```bash
python -m trading_bot.tools.e2e_demo_scenario
```

Output:
- Simulated day with 2 trades
- Shows entry/manage/exit/learn cycle
- Prints learning loop metrics
- Validates all components working together

**Time:** ~30 seconds

---

### Deployment Validation (Safety Checks)
**Run before paper or live trading.**

```bash
python -m trading_bot.tools.deployment_checklist
```

Validates:
- Safety limits configured correctly ($15 max risk, etc.)
- IBKR connection working
- Strategy library loaded
- Generates deployment report

**Time:** ~1 minute

---

### Paper Trading (IBKR Paper Mode)
**Recommended: Run for 1-2 trading days before live.**

```bash
# Start bot in OBSERVE mode (paper trading)
python -m trading_bot.cli --mode OBSERVE --adapter ibkr
```

What happens:
1. Connects to IBKR (paper mode)
2. Fetches account snapshot (should be ~$10k on paper)
3. Subscribes to market data (MES)
4. Starts main trading loop (every 1 minute bar)
5. Makes trades based on signals
6. Manages positions, records outcomes
7. Learning loop throttles/quarantines strategies

**Monitoring:**
- Logs: `data/trading_bot.log`
- Events: `data/events.sqlite`
- Decision journal: `data/decision_journal.log`

**Key things to verify:**
- [ ] Orders appearing in TWS
- [ ] Fills being recorded
- [ ] Positions updating correctly
- [ ] Kill switch working (test manually)
- [ ] Learning loop metrics updating
- [ ] No duplicate orders on restart

**Time:** Continuous (1-2 trading days)

---

### Live Trading (After Paper Validation)
**Only after 1-2 days of successful paper trading.**

```bash
# Start bot in LIVE mode (real capital)
python -m trading_bot.cli --mode LIVE --adapter ibkr
```

**⚠️ IMPORTANT:** 
- Start with small capital ($1k)
- Monitor closely first week
- Have kill switch ready
- Review every trade for first few days

---

## Daily Operations

### Before Market Open
```bash
# Validate deployment
python -m trading_bot.tools.deployment_checklist

# Check logs from previous day
tail -f data/trading_bot.log

# Review learning loop state
# (exported via learning_loop.export_to_dict())
```

### During Trading
```bash
# Monitor in real-time
# - Watch logs for kill switch events
# - Check TWS for order fills
# - Monitor P&L in account

# If issues arise:
# - Hit manual kill switch immediately
# - Review kill switch event log
# - Troubleshoot issue
# - Restart bot
```

### After Market Close
```bash
# Export daily report
python -m trading_bot.tools.export_daily_report

# Review trades and learning updates
# - Decision journal (why each entry/skip)
# - Trade journal (what happened)
# - Learning state (throttle levels, quarantines)

# Update strategy notes
# - Did any strategies get quarantined?
# - Any consistent loss patterns?
# - Adjust thresholds if needed
```

---

## Important Concepts

### Kill Switch
The bot has **automatic kill switch** that triggers on:
- Data quality failure (DVS < 0.30)
- Margin call (buying power < 0)
- Position desync (actual vs expected mismatch)
- Daily loss limit hit ($30)

Also has **manual kill switch**: One-click flatten all positions.

When triggered:
1. All positions flattened immediately
2. Event logged with timestamp and reason
3. No new orders accepted
4. Human review required to resume

### Risk Limits
- **Per trade:** $15 max risk (about 12 ticks on 1 contract)
- **Per day:** 2 trades max, $30 loss limit, 2 consecutive losses → lockout
- **Per account:** Margin buffer, tier gating by capital

### Learning Loop
- **Automatic:** Tracks win rate, expectancy per strategy
- **Throttling:** Adds friction (EUC 1.2x-1.5x) to underperformers
- **Quarantine:** Disables strategy on 2+ losses or negative expectancy
- **Re-enable:** Restores strategy on 2+ wins or recovery

### Reconciliation
- **On startup:** Compares broker positions to local state
- **On divergence:** Kill switch → flatten → human review
- **On fills:** Updates expected position
- **On disconnect:** Retries with exponential backoff

---

## Troubleshooting

### "Connection refused" (IBKR)
- [ ] TWS running?
- [ ] API enabled in TWS settings?
- [ ] Port correct (7497 paper, 7496 live)?
- [ ] Firewall blocking localhost?

### "No market data" or "DVS gated"
- [ ] Market data subscriptions active in TWS?
- [ ] During market hours?
- [ ] Check bar lag (should be < 5 seconds)
- [ ] Check for gaps (missing bars)

### "Kill switch triggered"
- Check log for reason (DVS failure, margin call, position desync, etc.)
- Fix root cause
- Restart bot
- Resume trading

### "Duplicate orders on restart"
- Verify idempotent order ID generation
- Check that order TTL/cancellation working
- Review reconciliation logic
- Should not happen if supervisor working correctly

### "Learning loop not updating"
- Check that trade outcomes being recorded
- Verify learning_loop.record_trade() being called
- Check decision metadata contains template_id and regime

---

## File Structure

```
trading-bot-v1/
├── src/trading_bot/
│   ├── adapters/                 # Broker adapters
│   ├── broker_gateway/           # IBKR integration
│   ├── contracts/                # Risk/execution contracts (YAML)
│   ├── core/                     # Core engines and runner
│   ├── engines/                  # Signal/belief/decision engines
│   ├── log/                      # Event store and logging
│   ├── strategies/               # Strategy templates
│   ├── tests/                    # Unit/integration tests
│   ├── tools/                    # CLI, demo, deployment
│   └── cli.py                    # Entry point
├── data/
│   ├── trading_bot.log           # Daily logs
│   ├── events.sqlite             # Event store
│   └── decision_journal.log      # Decision log
├── BUILD_SUMMARY.md              # What was built
└── PRODUCTION_READINESS.md       # Deployment checklist
```

---

## Key Files to Monitor

### Logs
- **data/trading_bot.log:** All bot activity (signals, decisions, fills, errors)
- **data/decision_journal.log:** Plain-English reasoning for each decision

### Database
- **data/events.sqlite:** Structured event store (EVENTS, FILLS, POSITIONS tables)

### Contracts
- **contracts/risk_model.yaml:** Safety limits ($15 max risk, etc.)
- **contracts/constitution.yaml:** Trading rules (session, tier gating, etc.)
- **contracts/data_contract.yaml:** DVS thresholds
- **contracts/execution_contract.yaml:** EQS thresholds, order TTL

---

## Example Scenarios

### Scenario 1: Morning Startup
```
1. Run deployment validation: python -m trading_bot.tools.deployment_checklist
2. Verify all checks pass
3. Start bot: python -m trading_bot.cli --mode OBSERVE --adapter ibkr
4. Monitor logs for first signal detection
5. Watch for first entry setup
```

### Scenario 2: Trade Entry to Exit
```
1. Bot detects K1 VWAP MR setup (DVS/EQS gates pass)
2. Entry signal generated, order placed
3. Position tracked, thesis monitored
4. Belief drops → thesis invalid → position exited
5. Trade outcome recorded (PnL, duration, reason)
6. Learning loop updates metrics (win/loss tracked)
7. If loss, K1 gets throttled (if 2nd loss, quarantined)
```

### Scenario 3: Kill Switch Trigger
```
1. Data quality failure detected (DVS < 0.30)
2. Kill switch activates automatically
3. All positions flattened immediately
4. Event logged: "KILL_SWITCH_TRIGGERED: DATA_QUALITY_FAILURE"
5. No new orders accepted
6. Human reviews logs
7. Once DVS recovers, human restarts bot
8. Reconciliation ensures no duplicate orders
9. Trading resumes
```

---

## Quick Checklist Before Paper Trading

- [ ] IBKR account set up (paper mode)
- [ ] TWS running with API enabled
- [ ] Market data subscriptions active
- [ ] Contracts validated (risk_model.yaml, constitution.yaml)
- [ ] E2E demo runs successfully
- [ ] Deployment validation passes
- [ ] Logs and monitoring set up
- [ ] Manual kill switch tested
- [ ] Team aware of operation

---

## Quick Checklist Before Live Trading

- [ ] 1-2 days of successful paper trading completed
- [ ] No kill switch events or issues observed
- [ ] Learning loop working correctly (metrics updating)
- [ ] Reconciliation working (no order mismatches)
- [ ] All safety limits validated
- [ ] Audit trail complete and auditable
- [ ] Deployment checklist passed
- [ ] Manual kill switch ready on desk
- [ ] Risk officer approved
- [ ] Team briefed on operation and risks
- [ ] Starting with small capital ($1k)

---

## Support

For issues, check:
1. **Logs:** `data/trading_bot.log`
2. **Event store:** Query `data/events.sqlite`
3. **Decision journal:** `data/decision_journal.log`
4. **Kill switch events:** Search logs for "KILL_SWITCH"
5. **Reconciliation errors:** Search logs for "RECONCILIATION"

---

**Status:** Production-Ready | Ready for Paper Trading  
**Last Updated:** December 26, 2025
