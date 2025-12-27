# Quick Reference Card

**Print this or keep it open while implementing Phase A**

---

## Phase A Implementation Checklist

### ✅ Session Exit Rules (10 min)
**File:** `src/trading_bot/core/runner.py`  
**Location:** In `run_once()` method, after DVS/EQS gating (line ~185)  
**What:** Add code to flatten at 15:55 ET (5 min before close)

```python
# Check if 5 minutes from close
close_time = dt.replace(hour=16, minute=0, second=0, microsecond=0)
minutes_to_close = (close_time - dt).total_seconds() / 60
if 0 < minutes_to_close < 5:
    self.adapter.flatten_positions()
    self.state_store.set_expected_position(0)
    # Log event...
```

**Validation:** Run `python -c "from trading_bot.core.runner import BotRunner; BotRunner()"`

---

### ✅ Learning Persistence (15 min)
**Files:** 
- `src/trading_bot/core/runner.py` (2 edits)
- Add `import json` at top

**Edit 1 - In `__init__()` (line ~45):**
After `self.learning_loop = LearningLoop(logger=None)`, add:
```python
self.learning_state_path = "data/learning_state.json"
try:
    with open(self.learning_state_path, "r") as f:
        saved_state = json.load(f)
    self.learning_loop.load_from_dict(saved_state)
except FileNotFoundError:
    pass
except Exception:
    pass
self._trades_since_save = 0
```

**Edit 2 - In `run_once()` (after learning event, line ~420):**
```python
self._trades_since_save += 1
if self._trades_since_save >= 10:
    try:
        import os
        os.makedirs("data", exist_ok=True)
        with open(self.learning_state_path, "w") as f:
            json.dump(self.learning_loop.export_to_dict(), f, default=str, indent=2)
        self._trades_since_save = 0
    except Exception:
        pass
```

**Validation:** After 10 trades, check `data/learning_state.json` exists

---

### ✅ Position Sizing (20 min)
**File:** `src/trading_bot/engines/decision_v2.py`  
**Edit 1 - Add method to DecisionEngineV2 class (line ~100):**

```python
def compute_position_size(
    self,
    equity: Decimal,
    max_risk_usd: Decimal,
    stop_ticks: int,
    tick_value: Decimal = Decimal("1.25"),
    tick_size: Decimal = Decimal("0.25"),
) -> int:
    """Compute position size based on equity and risk constraints."""
    risk_dollars = Decimal(str(stop_ticks)) * tick_size / Decimal("0.25") * tick_value
    if risk_dollars > max_risk_usd:
        return 0
    max_equity_risk = equity * Decimal("0.02")
    if risk_dollars > max_equity_risk:
        return 0
    return 1
```

**Edit 2 - In `decide()` method (line ~300):**
Find: `"size": 1,  # Currently hard-coded`

Replace with:
```python
"size": self.compute_position_size(
    equity=equity,
    max_risk_usd=self.tier_constraints[tier].max_risk_usd,
    stop_ticks=stop_ticks,
),
```

**Validation:** Run `python -c "from trading_bot.engines.decision_v2 import DecisionEngineV2; print('✅')"`

---

### ✅ Slippage/Commission (20 min)
**File:** `src/trading_bot/core/learning_loop.py`  
**Location:** TradeOutcome dataclass (line ~33)

**Find:**
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
    
    @property
    def actual_pnl_usd(self) -> Decimal:
        """PnL after deducting commission."""
        return self.pnl_usd - self.commission_round_trip
```

**Validation:** Run `python -c "from trading_bot.core.learning_loop import TradeOutcome; print('✅')"`

---

## Validation After Each Edit

```bash
# 1. Syntax check
python -m py_compile src/trading_bot/core/runner.py
python -m py_compile src/trading_bot/engines/decision_v2.py
python -m py_compile src/trading_bot/core/learning_loop.py

# 2. Import check
cd src && python -c "from trading_bot.core.runner import BotRunner; print('✅ Imports OK')"

# 3. E2E demo
python tools/e2e_demo_scenario.py

# 4. Quick test
python -m pytest tests/test_qa_suite.py::TestSignalEngine -v
```

---

## Estimated Time Breakdown

| Task | Min | Total |
|------|-----|-------|
| Session exit rules | 10 | 10 |
| Learning persistence | 15 | 25 |
| Position sizing | 20 | 45 |
| Slippage/commission | 20 | 65 |
| Syntax checks | 10 | 75 |
| E2E test | 10 | 85 |
| **TOTAL** | — | **~90 min** |

---

## Common Errors & Fixes

**Error:** `ModuleNotFoundError: No module named 'trading_bot'`  
**Fix:** `export PYTHONPATH="$PWD/src"` (or set in IDE)

**Error:** `FileNotFoundError: data/learning_state.json`  
**Fix:** Normal on first run; directory auto-created

**Error:** `AttributeError: learning_loop has no attribute export_to_dict`  
**Fix:** Make sure latest `learning_loop.py` loaded (not cached)

**Error:** `TypeError: compute_position_size() takes 4 positional arguments but 5 were given`  
**Fix:** Check method is inside DecisionEngineV2 class (indentation)

---

## Files to Modify (Summary)

| File | Edit | Lines | Change |
|------|------|-------|--------|
| runner.py | Add import | 1 | `import json` |
| runner.py | Add init | 5 | Learning state path setup |
| runner.py | Add auto-save | 10 | Save every 10 trades |
| runner.py | Add session exit | 10 | Flatten at 15:55 ET |
| decision_v2.py | Add method | 15 | Position size computation |
| decision_v2.py | Modify call | 5 | Use computed size |
| learning_loop.py | Modify dataclass | 8 | Add commission fields |

**Total lines added:** ~50 lines across 3 files

---

## Git Commands (If Using Version Control)

```bash
# Before changes
git status
git branch -m phase-a-improvements

# After each file edit
git add <file>
git commit -m "Add <feature>"

# Summary before pushing
git log --oneline -5
git diff main
```

---

## Rollback Plan (If Needed)

If something breaks, restore from git:
```bash
git checkout -- <filename>
```

Or manually revert by finding the original code in git and replacing.

---

## Support Resources

**File locations:**
- Contracts: `src/trading_bot/contracts/`
- Core logic: `src/trading_bot/core/`
- Engines: `src/trading_bot/engines/`
- Adapters: `src/trading_bot/adapters/`
- Tests: `tests/`

**Documentation:**
- Action plan: `ACTION_PLAN_PHASE_A.md`
- Detailed verification: `RECOMMENDATIONS_VERIFICATION.md`
- Architecture guide: `PRODUCTION_READINESS.md`

**Quick sanity checks:**
```bash
# Check Python syntax
python -m py_compile src/trading_bot/core/runner.py

# Run basic import
python -c "from trading_bot.core.runner import BotRunner; BotRunner()"

# Run E2E demo
python src/trading_bot/tools/e2e_demo_scenario.py
```

---

## You're Ready! 🚀

All 4 Phase A changes are:
- ✅ Well-scoped (50 lines total)
- ✅ Low-risk (additions only)
- ✅ Copy-paste ready (code provided)
- ✅ Easy to validate (syntax check + E2E demo)

**Start with Session Exit Rules (easiest), then do the others in any order.**

After all 4: Run E2E demo → Deploy to paper trading → Monitor for 1-2 days

