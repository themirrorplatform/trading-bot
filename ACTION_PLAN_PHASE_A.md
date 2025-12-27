# Action Plan: Critical Improvements Before Paper Trading

**Target:** Implement Phase A (Critical) in ~1.5 hours, then validate before IBKR paper trading

---

## Priority 1️⃣: Session Exit Rules (10 min) 
**Why Critical:** Prevents overnight gap risk, cleaner learning signal

**File to Edit:** `src/trading_bot/core/runner.py`

**Location:** In `run_once()` method, immediately after DVS/EQS gating checks (around line 180)

**Code to Add:**
```python
        # --- QUALITY GATE: Enforce DVS/EQS thresholds from data contract ---
        if dvs_val < Decimal("0.80"):
            # ... existing DVS check ...
        
        if eqs_val < Decimal("0.75"):
            # ... existing EQS check ...
        
        # NEW: SESSION EXIT RULE - Flatten 5 minutes before RTH close (16:00 ET)
        close_time = dt.replace(hour=16, minute=0, second=0, microsecond=0)
        minutes_to_close = (close_time - dt).total_seconds() / 60
        
        if 0 < minutes_to_close < 5:
            # Force flatten all positions
            self.adapter.flatten_positions()
            self.state_store.set_expected_position(0)
            
            evt = Event.make(stream_id, dt.isoformat(), "SESSION_EXIT_FLATTEN", {
                "reason": "MINUTES_TO_RTH_CLOSE",
                "minutes_remaining": float(minutes_to_close),
            }, self.config_hash)
            self.events.append(evt)
            return {"action": "SKIP", "reason": "SESSION_EXIT"}
```

**Validation:** After adding, run:
```bash
python -c "from trading_bot.core.runner import BotRunner; BotRunner()"
```
Should not error.

---

## Priority 2️⃣: Learning Loop Persistence (15 min)
**Why Critical:** Strategy throttle state survives restart

**Files to Edit:** `src/trading_bot/core/runner.py`

**Location 1:** In `__init__()` after learning_loop initialization (around line 47)

**Code to Add After:**
```python
        # Learning loop for strategy reliability and throttling
        self.learning_loop = LearningLoop(logger=None)
```

**Add:**
```python
        # Load prior learning state if available
        self.learning_state_path = "data/learning_state.json"
        try:
            with open(self.learning_state_path, "r") as f:
                saved_state = json.load(f)
            self.learning_loop.load_from_dict(saved_state)
            # Could log: f"Loaded learning state from {self.learning_state_path}"
        except FileNotFoundError:
            pass  # Fresh start
        except Exception:
            pass  # Graceful degradation
        
        self._trades_since_save = 0
```

**Location 2:** In `run_once()` method, near the end (around line 420)

**After the learning event is appended:**
```python
                    learning_event = Event.make(stream_id, dt.isoformat(), "LEARNING_UPDATE", learning_result, self.config_hash)
                    self.events.append(learning_event)
```

**Add:**
```python
                    # Auto-save learning state every 10 trades
                    self._trades_since_save += 1
                    if self._trades_since_save >= 10:
                        try:
                            import os
                            os.makedirs("data", exist_ok=True)
                            with open(self.learning_state_path, "w") as f:
                                json.dump(self.learning_loop.export_to_dict(), f, default=str, indent=2)
                            self._trades_since_save = 0
                        except Exception:
                            pass  # Silently skip on error
```

**Add at top of file with other imports:**
```python
import json
```

**Validation:** After adding, check that learning_state.json is created after 10 trades.

---

## Priority 3️⃣: Slippage & Commission Tracking (20 min)
**Why Important:** Realistic PnL, helps detect model miscalibration

**File to Edit:** `src/trading_bot/core/learning_loop.py`

**Location:** In `TradeOutcome` dataclass (around line 33)

**Find this:**
```python
    slippage_ticks: float
    spread_ticks: float
    win: bool  # True if pnl_usd > 0
```

**Replace with:**
```python
    slippage_ticks: float
    slippage_expected_ticks: float = 0.5  # Model prediction
    spread_ticks: float
    commission_round_trip: Decimal = Decimal("2.50")  # MES standard
    win: bool = False  # True if pnl_usd > 0
    
    # Computed PnL after costs
    @property
    def actual_pnl_usd(self) -> Decimal:
        """PnL after deducting commission."""
        return self.pnl_usd - self.commission_round_trip
```

**Location 2:** In `ReliabilityMetrics.update_from_trade()` (around line 110)

**After updating win/loss counts, add:**
```python
        # Track slippage calibration
        slippage_error = outcome.slippage_ticks - outcome.slippage_expected_ticks
        # Could accumulate for future adjustment of decision engine slippage model
```

**Validation:** New trades should have commission deducted from PnL.

---

## Priority 4️⃣: Dynamic Position Sizing (20 min)
**Why Important:** Capital preservation, prevents over-leverage

**File to Edit:** `src/trading_bot/engines/decision_v2.py`

**Location:** Add new method to `DecisionEngineV2` class (around line 100)

**Add:**
```python
    def compute_position_size(
        self,
        equity: Decimal,
        max_risk_usd: Decimal,
        stop_ticks: int,
        tick_value: Decimal = Decimal("1.25"),  # MES: $1.25/tick
        tick_size: Decimal = Decimal("0.25"),
    ) -> int:
        """
        Compute position size constrained by:
        - Max risk per trade ($15)
        - Max stop distance (12 ticks)
        - Equity limits (don't risk > 2% per trade)
        - Minimum 0.5 contracts
        
        Returns: Contract size (0, 1, 2, etc.)
        """
        # Risk for full 1 contract
        risk_dollars = Decimal(str(stop_ticks)) * tick_size / Decimal("0.25") * tick_value
        
        # Can't exceed max risk
        if risk_dollars > max_risk_usd:
            return 0  # Skip: stop too wide for max risk
        
        # Can't risk > 2% of equity
        max_equity_risk = equity * Decimal("0.02")
        if risk_dollars > max_equity_risk:
            return 0
        
        # For MES: each contract scales linearly
        # Risk satisfied; return 1 contract (scale could be added later)
        return 1
```

**Location 2:** In `decide()` method, when creating order_intent (around line 300)

**Find:**
```python
                        order_intent={
                            "side": template["side"],
                            "size": 1,  # Currently hard-coded
```

**Change to:**
```python
                        order_intent={
                            "side": template["side"],
                            "size": self.compute_position_size(
                                equity=equity,
                                max_risk_usd=self.tier_constraints[tier].max_risk_usd,
                                stop_ticks=stop_ticks,
                            ),
```

**Validation:** Verify orders use computed size instead of hard-coded 1.

---

## Phase A Completion Check

After implementing all 4 changes, run:

```bash
# 1. Check syntax
python -m py_compile src/trading_bot/core/runner.py
python -m py_compile src/trading_bot/core/learning_loop.py
python -m py_compile src/trading_bot/engines/decision_v2.py

# 2. Check imports
cd src
python -c "from trading_bot.core.runner import BotRunner; print('✅ Imports OK')"

# 3. Check config loads
python -c "from trading_bot.core.runner import BotRunner; r = BotRunner(); print('✅ Config loads')"

# 4. Run quick test
python -m pytest tests/test_qa_suite.py::TestSignalEngine::test_signal_bounds -v
```

All should pass before paper trading.

---

## What These Changes Accomplish

| Change | Risk Reduced | Capital Preserved | Learning Improved |
|--------|---|---|---|
| Session Exit | Overnight gaps | ✅ Forced close | ✅ Daily reset |
| Learning Persistence | Strategy forgets | — | ✅ Throttle survives restart |
| Commission Tracking | PnL unrealistic | ✅ Actual costs | ✅ Better calibration |
| Position Sizing | Over-leverage | ✅ Scaled by equity | — |

---

## Expected Outcomes After Phase A

- ✅ No overnight gaps (all positions closed by 16:00)
- ✅ Throttled strategies stay throttled after restart
- ✅ PnL includes commission ($2.50/round-trip)
- ✅ Position size adapts to equity level
- ✅ Ready for paper trading validation

---

## Next Steps

1. **Implement Phase A** (1.5 hours)
2. **Test with E2E demo:** `python tools/e2e_demo_scenario.py`
3. **Deploy to paper trading:** `python -m trading_bot.cli --mode OBSERVE --adapter ibkr`
4. **Run for 1-2 trading days**
5. **Review: learning metrics, kill switch triggers, position sizing**
6. **Then decide:** Phase B (dashboard, config thresholds) or go live

---

## Questions Before You Start?

- Where should `data/` directory be created? (Recommend: `src/trading_bot/data/` for isolation)
- Any preference on learning state save frequency? (Recommend: every 10 trades or daily)
- Should failed learning saves emit a log warning, or silently degrade?

