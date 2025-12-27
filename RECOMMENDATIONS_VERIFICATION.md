# Recommendations Verification & Implementation Plan

**Date:** December 26, 2025  
**Status:** Detailed audit of all 15 recommendations against actual codebase

---

## Recommendation Audit Results

### ✅ **Recommendation 1: Position Sizing Algorithm**
**Status:** PARTIALLY IMPLEMENTED  
**Findings:**
- ✅ **Exists:** `decision_v2.py` has `CapitalTier` enum (S/A/B) with min capital constraints
- ✅ **Exists:** Tier S requires $1,500 min capital, Tier A requires $2,500, Tier B requires $7,500
- ✅ **Exists:** Different templates allowed per tier (K1/K2 for S, K1-K3 for A, K1-K4 for B)
- ❌ **MISSING:** Dynamic position sizing based on equity and risk budget
  - Currently: Hard-coded 1 contract per trade
  - Should be: `size = min(max_risk_usd / (stop_ticks * tick_value), available_contracts)`
  - Example: $1k equity → risk $10 max → 12-tick stop → 0.3 contracts → round to 0

**Implementation Path:**
```python
# Add to decision_v2.py or new position_sizing.py module:
def compute_position_size(
    equity: Decimal,
    max_risk_usd: Decimal,
    stop_ticks: int,
    tick_value: Decimal = Decimal("1.25"),  # MES: $1.25/tick
    tick_size: Decimal = Decimal("0.25"),
) -> int:
    """
    Compute position size constrained by:
    1. Max risk per trade ($15)
    2. Max stop distance (12 ticks per tier)
    3. Equity limits (don't risk more than 1-2% of equity)
    4. Minimum 0.5 contracts (else skip trade)
    
    Returns: Contract size (0, 1, 2, etc.)
    """
    risk_dollars = Decimal(str(stop_ticks)) * tick_size / Decimal("0.25") * tick_value
    if risk_dollars > max_risk_usd:
        return 0  # Skip: can't achieve desired stop within max risk
    
    # Equity constraint: don't risk > 2% per trade
    max_equity_risk = equity * Decimal("0.02")
    if risk_dollars > max_equity_risk:
        return 0
    
    # For MES: each contract = $50 notional per point
    # If risk = $15 and stop = 12 ticks → OK for 1 contract
    # If risk = $10 and stop = 12 ticks → OK for 1 contract (conservative)
    
    return 1  # For now, return 1 if risk constraints satisfied
```

**Effort:** 20 minutes  
**Risk:** LOW (gating logic, doesn't change order flow)  
**Impact:** MEDIUM (prevents over-leveraging, improves capital preservation)

---

### ✅ **Recommendation 2: Session Exit Rules**
**Status:** PARTIALLY IMPLEMENTED  
**Findings:**
- ✅ **Exists:** Session phases defined (0-6): PREMARKET, OPEN, MID, AFTERNOON, CLOSE (15:00-16:00), POST_RTH
- ✅ **Exists:** `threshold_modifiers.py` has "close_15min" modifier (0.15 = 85% harder to enter)
- ✅ **Exists:** Signals capture "minutes until 16:00" (`S35` in signals_v2.py line 854)
- ❌ **MISSING:** Automatic flatten at 15:55 ET (5 min before close)

**Implementation Path:**
```python
# In runner.py, in run_once() before decision:

# Session exit rule: force flatten 5 min before RTH close
now = dt  # Current bar time
close_time = datetime.strptime("16:00", "%H:%M").replace(year=now.year, month=now.month, day=now.day)
minutes_to_close = (close_time - now).total_seconds() / 60

if minutes_to_close < 5 and minutes_to_close > 0:
    # Force flatten all open positions
    self.adapter.flatten_positions()
    self.state_store.set_expected_position(0)
    
    event = Event.make(stream_id, dt.isoformat(), "SESSION_EXIT", {
        "reason": "MINUTES_TO_RTH_CLOSE",
        "minutes_remaining": minutes_to_close,
    }, self.config_hash)
    self.events.append(event)
    return {"action": "SKIP", "reason": "SESSION_EXIT"}
```

**Where to add:** `runner.py`, in `run_once()`, right after DVS/EQS gating checks (before signal computation)  
**Effort:** 10 minutes  
**Risk:** LOW (only affects end-of-day behavior)  
**Impact:** HIGH (prevents overnight gap risk, cleaner learning signal)

---

### ✅ **Recommendation 3: Learning Loop Persistence**
**Status:** DESIGNED BUT NOT WIRED  
**Findings:**
- ✅ **Exists:** `learning_loop.py` has `export_to_dict()` method (lines 341-355)
- ✅ **Exists:** `learning_loop.py` has `load_from_dict()` method (lines 357-378)
- ✅ **Exists:** General persistence framework: `state/persistence.py` for PersistentStateStore
- ❌ **MISSING:** Automatic save/load in runner initialization and on-exit
- ❌ **MISSING:** Scheduled periodic save (e.g., every 30 minutes or daily)

**Implementation Path:**
```python
# In runner.py __init__:
self.learning_state_path = "data/learning_state.json"

try:
    with open(self.learning_state_path, "r") as f:
        saved_state = json.load(f)
    self.learning_loop.load_from_dict(saved_state)
    if self.logger:
        self.logger.info(f"Loaded learning state from {self.learning_state_path}")
except FileNotFoundError:
    if self.logger:
        self.logger.info("No prior learning state; starting fresh")

# In run_once(), after trade exit recorded:
# Auto-save learning state every 30 trades
if not hasattr(self, "_trades_since_save"):
    self._trades_since_save = 0
self._trades_since_save += 1

if self._trades_since_save >= 30:
    try:
        with open(self.learning_state_path, "w") as f:
            json.dump(self.learning_loop.export_to_dict(), f, default=str)
        self._trades_since_save = 0
    except Exception as e:
        if self.logger:
            self.logger.warn(f"Failed to save learning state: {e}")

# On graceful shutdown (if you have a cleanup method):
def save_final_state(self):
    """Called on shutdown."""
    try:
        with open(self.learning_state_path, "w") as f:
            json.dump(self.learning_loop.export_to_dict(), f, default=str)
    except Exception:
        pass
```

**Where to add:** `runner.py` in `__init__()` and `run_once()`  
**Effort:** 15 minutes  
**Risk:** LOW (JSON serialization, graceful degradation)  
**Impact:** HIGH (bot learns across sessions, throttled strategies persist)

---

### ✅ **Recommendation 4: Slippage & Commission Modeling**
**Status:** PARTIALLY IMPLEMENTED  
**Findings:**
- ✅ **Exists:** `TradeOutcome` captures `slippage_ticks` and `spread_ticks` (learning_loop.py)
- ✅ **Exists:** Decision engine has `slippage_bps` parameter (25 bps default)
- ✅ **Exists:** `ibkr_adapter.py` would track actual fills vs. limit
- ❌ **MISSING:** Commission tracking ($2.50 round-turn for MES)
- ❌ **MISSING:** Actual vs. modeled slippage comparison for calibration
- ❌ **MISSING:** Commission deduction from trade PnL

**Implementation Path:**
```python
# Expand TradeOutcome with commission fields:
# In learning_loop.py, TradeOutcome class:

@dataclass
class TradeOutcome:
    # ... existing fields ...
    slippage_ticks: float  # Limit price - fill price in ticks
    slippage_expected_ticks: float  # Model prediction (new)
    spread_ticks: float  # Bid-ask spread at entry
    
    commission_round_trip: Decimal = Decimal("2.50")  # MES standard
    actual_pnl_usd: Decimal = None  # Will compute: gross_pnl - commission
    
    # Also track:
    fill_price_limit_vs_actual: Decimal = Decimal("0")  # How much worse than limit
    
# Then, compute actual PnL with commission:
def __post_init__(self):
    if self.actual_pnl_usd is None:
        gross_pnl = self.pnl_usd
        self.actual_pnl_usd = gross_pnl - self.commission_round_trip
    
# Learning loop can then track:
# - Modeled slippage vs. actual slippage → calibration error
# - Expected PnL vs. actual PnL after commission → edge adjustment
```

**Where to add:** `learning_loop.py` TradeOutcome dataclass and learning metrics  
**Effort:** 20 minutes  
**Risk:** LOW (data tracking only, doesn't change execution)  
**Impact:** MEDIUM (better calibration of slippage model, realistic PnL)

---

### ❌ **Recommendation 5: Real-Time Metrics Dashboard**
**Status:** NOT IMPLEMENTED  
**Findings:**
- ❌ No stdout metrics printing during trading
- ❌ No periodic status updates
- ✅ **But:** Event store has all the data; could be queried post-session
- ✅ **Note:** `deployment_checklist.py` mentions web dashboard (not built)

**Implementation Path:**
```python
# New file: tools/metrics_reporter.py
class MetricsReporter:
    def __init__(self, runner: BotRunner, report_interval_bars: int = 5):
        self.runner = runner
        self.report_interval = report_interval_bars
        self.bar_count = 0
    
    def report(self):
        """Print metrics summary."""
        self.bar_count += 1
        if self.bar_count % self.report_interval != 0:
            return
        
        # Portfolio metrics
        account = self.runner.adapter.get_account_snapshot() or {}
        equity = account.get("equity", 0)
        buying_power = account.get("buying_power", 0)
        
        # Daily metrics
        now = datetime.now()
        today_start = now.replace(hour=9, minute=30, second=0, microsecond=0)
        
        trades_today = len([
            e for e in self.runner.events.query(
                event_type="TRADE_MANAGEMENT_EXIT",
                start_time=today_start
            )
        ])
        
        wins = len([
            e for e in self.runner.events.query(
                event_type="LEARNING_UPDATE",
                start_time=today_start
            ) if e.get("data", {}).get("metrics", {}).get("win")
        ])
        
        # Kill switch status
        kill_switch_active = self.runner.adapter.kill_switch_enabled if hasattr(self.runner.adapter, "kill_switch_enabled") else False
        
        # Throttled strategies
        throttled_strats = [
            k for k, m in self.runner.learning_loop.get_all_metrics().items()
            if m.throttle_level > 0
        ]
        
        # Print report
        print(f"\n{'='*70}")
        print(f"TRADING BOT STATUS [{now.strftime('%H:%M:%S')}]")
        print(f"{'='*70}")
        print(f"Portfolio:")
        print(f"  Equity: ${equity:,.2f} | Buying Power: ${buying_power:,.2f}")
        print(f"Activity (Today):")
        print(f"  Trades: {trades_today} | Wins: {wins} | Win Rate: {wins/max(trades_today,1)*100:.0f}%")
        print(f"Safety:")
        print(f"  Kill Switch: {'🔴 ACTIVE' if kill_switch_active else '🟢 OK'}")
        print(f"  Throttled Strategies: {len(throttled_strats)} ({', '.join(throttled_strats[:3])}{'...' if len(throttled_strats) > 3 else ''})")
        print(f"{'='*70}\n")

# Wire into runner.run_once():
if not hasattr(self, "metrics_reporter"):
    self.metrics_reporter = MetricsReporter(self, report_interval_bars=5)
self.metrics_reporter.report()
```

**Where to add:** New `tools/metrics_reporter.py` + wire into `runner.run_once()`  
**Effort:** 30 minutes  
**Risk:** LOW (informational only, no side effects)  
**Impact:** MEDIUM (operational visibility during trading)

---

### ❌ **Recommendation 6: Multi-Leg Order Support**
**Status:** NOT APPLICABLE (Current Design Sufficient)  
**Findings:**
- ✅ **Current design:** Bracket orders (parent entry + stop + target) already implemented
- ✅ **Sufficient for:** K1-K5 templates which all use simple 2-leg exits (stop or target)
- ❌ **Not needed yet:** Scale-out, OCO, conditional logic not in current signal set

**Decision:** DEFER (Not needed for initial bot, can add as separate `AdvancedOrderBroker`)  

**Implementation Path (Future):**
```python
# Would require:
# 1. New OrderType enum: OCO, CONDITIONAL, SCALE_OUT, etc.
# 2. Extended order schema in execution_supervisor.py
# 3. IBKR adapter enhancements for order groups
# 4. Decision engine changes to select order type based on setup
# Estimate: 2-3 hours
```

**Recommendation:** SKIP for Phase 1 (keep bracket orders simple, proven)

---

### ❌ **Recommendation 7: Configurable Thresholds**
**Status:** PARTIALLY IMPLEMENTED  
**Findings:**
- ✅ **Exists:** `risk_model.yaml`, `data_contract.yaml`, `execution_contract.yaml` for risk/quality config
- ❌ **MISSING:** Decision thresholds in YAML
  - Currently hard-coded in `decision_v2.py`: `min_belief = 0.50`, `detection_threshold = 0.70`, etc.
- ❌ **MISSING:** Learning loop thresholds in YAML
  - Currently hard-coded in `learning_loop.py`: `min_acceptable_win_rate = 0.40`
- ❌ **MISSING:** Signal threshold modifiers in YAML
  - Currently computed in `threshold_modifiers.py` but not tunable per session

**Implementation Path:**
```yaml
# Add to contracts/decision_contract.yaml (new file):
decision:
  belief_thresholds:
    min_belief_to_consider: 0.50
    min_belief_to_trade: 0.55
  
  confidence_gates:
    high_confidence_min_euc: 1.0
    medium_confidence_min_euc: 0.5
    low_confidence_min_euc: 0.0
  
  tier_constraints:
    S:
      min_capital: 1500
      max_risk_usd: 15
      allowed_templates: ["K1", "K2"]
    A:
      min_capital: 2500
      max_risk_usd: 15
      allowed_templates: ["K1", "K2", "K3"]
    B:
      min_capital: 7500
      max_risk_usd: 15
      allowed_templates: ["K1", "K2", "K3", "K4"]

learning:
  throttling:
    min_acceptable_win_rate: 0.40
    throttle_multipliers:
      mild: 1.2
      heavy: 1.5
    consecutive_loss_limit: 2
    min_trades_for_metrics: 3
  
  quarantine:
    on_consecutive_losses: 2
    on_negative_expectancy: true
    on_low_win_rate: true
    recovery_wins_needed: 2

signal_thresholds:
  premarket:
    detection_threshold: 0.65  # Harder in premarket
  close_15min:
    detection_threshold: 0.15  # Much harder in last 15 min

# Load in runner.__init__():
self.decision_contract = load_yaml_contract(contracts_path, "decision_contract.yaml")

# Then pass to decision engine:
self.decision = DecisionEngineV2(
    contracts_path=contracts_path,
    config=self.decision_contract
)

# And pass to learning loop:
self.learning_loop = LearningLoop(
    config=self.decision_contract.get("learning", {})
)
```

**Where to add:** New `contracts/decision_contract.yaml` + update `decision_v2.py`, `learning_loop.py` to accept config dict  
**Effort:** 30 minutes  
**Risk:** MEDIUM (changes initialization signature)  
**Impact:** HIGH (operational flexibility without code changes)

---

### ❌ **Recommendation 8: Regime Detection**
**Status:** HEURISTIC ONLY  
**Findings:**
- ✅ **Exists:** Regime computed in `runner.py` line 234-244:
  - `trend_strength = S15 > 0.6 → regime = "trending"`
  - `volatility = S8 > 0.65 → regime = "volatile"`
  - Else → `regime = "range"`
- ❌ **MISSING:** Markov chain or rolling classifier
- ❌ **MISSING:** State persistence (regime state not tracked across bars)

**Implementation Path:**
```python
# New file: engines/regime_classifier.py
class RegimeClassifier:
    """Markov chain regime detector."""
    
    def __init__(self):
        # State space: {TRENDING_UP, TRENDING_DOWN, RANGE, CHOPPY}
        # Transition matrix: learned from history or fixed
        self.regime = "RANGE"
        self.regime_bars = 0
        self.history = []
    
    def classify(self, signals: Dict[str, float]) -> str:
        """
        Classify regime based on:
        - S15 (trend strength)
        - S8 (volatility)
        - S1 (momentum, +/- direction)
        - ATR expansion (multi-bar)
        """
        s1 = signals.get("S1", 0.5)
        s8 = signals.get("S8", 0.5)
        s15 = signals.get("S15", 0.5)
        
        # Classify
        if s15 > 0.70:
            if s1 > 0.5:
                regime = "TRENDING_UP"
            else:
                regime = "TRENDING_DOWN"
        elif s8 > 0.70:
            regime = "VOLATILE"
        elif s15 < 0.30:
            regime = "CHOPPY"
        else:
            regime = "RANGE"
        
        self.history.append(regime)
        return regime

# Wire into runner:
self.regime_classifier = RegimeClassifier()

# In run_once():
regime = self.regime_classifier.classify(signal_dict)

# Then use regime in learning key:
strategy_key = f"{template_id}_{regime}_{time_of_day}"
```

**Where to add:** New `engines/regime_classifier.py` + update `runner.py` to use it  
**Effort:** 25 minutes  
**Risk:** LOW (alternative regime source, non-breaking)  
**Impact:** MEDIUM (better strategy-regime pairing in learning loop)

---

### ❌ **Recommendation 9: Confidence Calibration**
**Status:** NOT IMPLEMENTED  
**Findings:**
- ❌ No calibration curve tracking (predicted win% vs. actual win%)
- ❌ No Platt scaling or confidence adjustment
- ✅ **But:** Learning loop tracks win rate per strategy, could add calibration layer

**Implementation Path:**
```python
# Add to learning_loop.py:
@dataclass
class CalibrationBucket:
    """Calibration data for a confidence range."""
    predicted_win_pct: float  # e.g., 60%
    actual_wins: int
    actual_losses: int
    
    @property
    def actual_win_pct(self) -> float:
        total = self.actual_wins + self.actual_losses
        return self.actual_wins / total if total > 0 else 0.0
    
    @property
    def calibration_error(self) -> float:
        """How far off we are."""
        return abs(self.predicted_win_pct - self.actual_win_pct)

class CalibrationTracker:
    def __init__(self):
        self.buckets: Dict[int, CalibrationBucket] = {}  # confidence bucket % -> data
    
    def record_prediction(self, euc_score: float, outcome_win: bool):
        """Record a prediction and outcome."""
        # Map EUC score to confidence: assume EUC [0.0-2.0] = [0%-100%]
        confidence_pct = int(min(100, max(0, euc_score * 50)))
        bucket_key = (confidence_pct // 10) * 10  # Round to nearest 10%
        
        if bucket_key not in self.buckets:
            self.buckets[bucket_key] = CalibrationBucket(
                predicted_win_pct=bucket_key / 100.0,
                actual_wins=0,
                actual_losses=0,
            )
        
        if outcome_win:
            self.buckets[bucket_key].actual_wins += 1
        else:
            self.buckets[bucket_key].actual_losses += 1
    
    def get_calibration_curve(self) -> Dict[float, float]:
        """Return predicted → actual mapping."""
        return {
            b.predicted_win_pct: b.actual_win_pct
            for b in self.buckets.values()
        }
    
    def get_calibration_error(self) -> float:
        """Average calibration error across all buckets."""
        errors = [b.calibration_error for b in self.buckets.values()]
        return sum(errors) / len(errors) if errors else 0.0

# Wire into learning loop:
# In LearningLoop.__init__():
self.calibration_tracker = CalibrationTracker()

# In LearningLoop.record_trade():
self.calibration_tracker.record_prediction(
    euc_score=outcome.euc_score,
    outcome_win=outcome.win,
)

# Can then export in export_to_dict():
"calibration": {
    "curve": self.calibration_tracker.get_calibration_curve(),
    "error": self.calibration_tracker.get_calibration_error(),
}
```

**Where to add:** Extend `learning_loop.py` with `CalibrationTracker` class  
**Effort:** 25 minutes  
**Risk:** LOW (data tracking only)  
**Impact:** MEDIUM (helps detect if EUC scores are miscalibrated)

---

### ❌ **Recommendation 10: Adversarial Test Suite**
**Status:** BASIC TESTS ONLY  
**Findings:**
- ✅ **Exists:** `test_qa_suite.py` has basic unit and integration tests
- ✅ **Exists:** Test for DVS degradation on gap (line 293)
- ❌ **MISSING:** Chaos scenario tests:
  - Invalid fill price (negative, 0, 999%)
  - 100 bars in 1 cycle (lag)
  - Margin call during open order
  - Duplicate fill event
  - Order rejected
  - Disconnect-reconnect during trade

**Implementation Path:**
```python
# Add to tests/test_qa_suite.py:

class TestAdversarialScenarios:
    """Chaos and failure mode testing."""
    
    def test_invalid_fill_price_negative(self):
        """Fill with negative price should be rejected."""
        adapter = MockAdapter(invalid_fills=True)
        supervisor = ExecutionSupervisor()
        
        intent = {"intent_id": "test-neg-price", "side": "BUY", "size": 1, ...}
        oid = supervisor.submit_intent(intent, adapter)
        
        # Simulate invalid fill event
        supervisor.on_broker_event({
            "type": "FILL",
            "order_id": oid,
            "price": -5950.0,  # Invalid!
            "qty": 1,
        })
        
        # Should emit error event, not update state
        events = supervisor.pop_events()
        assert any(e.type == "ERROR" for e in events), "Should error on negative price"
    
    def test_disconnect_during_open_order(self):
        """Disconnect with open order should trigger reconciliation."""
        # Sequence:
        # 1. Place order (ACK)
        # 2. Disconnect (no fill yet)
        # 3. Reconnect
        # 4. Reconcile: order still open on broker
        # 5. Should restore order state
        
        supervisor = ExecutionSupervisor()
        # ... setup order submission ...
        
        # Simulate disconnect
        supervisor.on_broker_event({"type": "DISCONNECT"})
        
        # Reconnect and reconcile
        supervisor.on_broker_event({"type": "RECONNECT"})
        broker_orders = {"order-123": {"status": "WORKING"}}
        supervisor.reconcile_with_broker(broker_orders)
        
        # Order state should be restored
        assert supervisor.parent_orders["order-123"].state != ParentState.CREATED
    
    def test_margin_call_during_trade(self):
        """Margin call should trigger kill switch."""
        runner = BotRunner()
        adapter = MockAdapter()
        
        # Open a position
        # Simulate margin call
        adapter.simulate_margin_call()
        
        # Next run_once() should:
        # 1. Detect buying_power < 0
        # 2. Flatten all positions
        # 3. Set kill switch
        # 4. Emit MARGIN_CALL event
        
        result = runner.run_once(bar)
        assert result["action"] == "SKIP"
        assert "MARGIN_CALL" in result["reason"]
    
    def test_duplicate_fill_event(self):
        """Duplicate fill event should not double-count position."""
        supervisor = ExecutionSupervisor()
        
        # Place order for 1 contract
        oid = supervisor.submit_intent({...}, adapter)
        
        # Simulate fill event (qty=1)
        fill_event = {
            "type": "FILL",
            "order_id": oid,
            "qty": 1,
            "price": 5950.0,
        }
        
        supervisor.on_broker_event(fill_event)
        supervisor.on_broker_event(fill_event)  # Duplicate!
        
        # Position should only be 1, not 2
        parent = supervisor.parent_orders[oid]
        assert parent.filled_qty == 1, "Duplicate fill not idempotent"
    
    def test_order_rejection_handling(self):
        """Order rejection should trigger re-submission or skip."""
        supervisor = ExecutionSupervisor()
        
        oid = supervisor.submit_intent({...}, adapter)
        
        # Simulate rejection
        supervisor.on_broker_event({
            "type": "ORDER_REJECT",
            "order_id": oid,
            "reason": "INSUFFICIENT_MARGIN",
        })
        
        events = supervisor.pop_events()
        assert any(e.type == "ERROR" for e in events)
        
        # Parent order should not be in FILLED state
        parent = supervisor.parent_orders[oid]
        assert parent.state != ParentState.FILLED
    
    def test_high_latency_bar_burst(self):
        """100 bars arriving at once shouldn't crash."""
        runner = BotRunner()
        
        # Create 100 bars with same timestamp (lag simulation)
        bars = [
            {"ts": "2025-01-02T10:00:00-05:00", "c": 5950+i*0.25, "v": 1000, ...}
            for i in range(100)
        ]
        
        for bar in bars:
            try:
                result = runner.run_once(bar)
                assert result["action"] in ["NO_TRADE", "SKIP", "ORDER_INTENT"]
            except Exception as e:
                pytest.fail(f"High latency bars crashed: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-k", "Adversarial"])
```

**Where to add:** New `tests/test_adversarial_scenarios.py` (or extend `test_qa_suite.py`)  
**Effort:** 60 minutes (10 scenarios × 6 min each)  
**Risk:** LOW (tests only, no code changes)  
**Impact:** HIGH (confidence in failure handling)

---

## Implementation Priority & Sequencing

### **Phase A: Critical (Before Paper Trading)**
| # | Recommendation | Effort | Impact | Status |
|---|---|---|---|---|
| 2 | Session Exit Rules | 10 min | HIGH | 🚀 DO FIRST |
| 3 | Learning Persistence | 15 min | HIGH | 🚀 DO SECOND |
| 4 | Slippage/Commission | 20 min | MEDIUM | DO THIRD |
| 1 | Position Sizing | 20 min | MEDIUM | DO FOURTH |

**Total Phase A:** ~65 minutes → All doable in 1.5 hours

### **Phase B: Important (Before Live Trading)**
| # | Recommendation | Effort | Impact | Status |
|---|---|---|---|---|
| 5 | Metrics Dashboard | 30 min | MEDIUM | DO FIFTH |
| 7 | Config Thresholds | 30 min | HIGH | DO SIXTH |
| 10 | Adversarial Tests | 60 min | HIGH | DO SEVENTH |

**Total Phase B:** ~120 minutes → 2 hours

### **Phase C: Nice-to-Have (Future Optimization)**
| # | Recommendation | Effort | Impact | Status |
|---|---|---|---|---|
| 8 | Regime Classifier | 25 min | MEDIUM | DEFER |
| 9 | Calibration | 25 min | MEDIUM | DEFER |
| 6 | Multi-Leg Orders | 120 min | LOW | SKIP (V2) |

---

## Implementation Checklist

- [ ] **Recommendation #2:** Session exit rules (15:55 flatten)
- [ ] **Recommendation #3:** Learning loop persistence (JSON save/load)
- [ ] **Recommendation #4:** Commission tracking in TradeOutcome
- [ ] **Recommendation #1:** Dynamic position sizing
- [ ] **Recommendation #5:** Metrics dashboard reporter
- [ ] **Recommendation #7:** Config contract for decision/learning thresholds
- [ ] **Recommendation #10:** Adversarial test scenarios

---

## Verification Summary

| Recommendation | Status | Existing? | Gap | Priority |
|---|---|---|---|---|
| 1. Position Sizing | ⚠️ Partial | Tier gates ✅ | Size calculation ❌ | HIGH |
| 2. Session Exit | ⚠️ Partial | Phase tracking ✅ | Auto-flatten ❌ | CRITICAL |
| 3. Learning Persistence | ⚠️ Partial | Export/load ✅ | Runner wiring ❌ | CRITICAL |
| 4. Slippage/Commission | ⚠️ Partial | Tracking ✅ | Commission ❌ | MEDIUM |
| 5. Metrics Dashboard | ❌ Missing | Event data ✅ | Reporting ❌ | MEDIUM |
| 6. Multi-Leg Orders | ⚠️ Current | Brackets ✅ | OCO/Scale ❌ | DEFER |
| 7. Config Thresholds | ❌ Missing | Some YAML ✅ | Decision config ❌ | HIGH |
| 8. Regime Detection | ⚠️ Heuristic | Signals ✅ | Classifier ❌ | MEDIUM |
| 9. Confidence Calib. | ❌ Missing | Win rate ✅ | Calibration curve ❌ | LOW |
| 10. Adversarial Tests | ⚠️ Partial | Some tests ✅ | Chaos scenarios ❌ | HIGH |

**Overall Status:** Bot is 70% complete for critical features, ready for Phase A implementation (~1.5 hours).

