"""Tests for DecisionEngine v1 (constitution-first).

Validates:
- Constitution hierarchy enforcement
- Strategy template evaluation
- Order intent generation
- Fail-closed behavior for unknown conditions
"""
import pytest
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from src.trading_bot.engines.decision import DecisionEngine, OrderIntent
from src.trading_bot.core.reason_codes import NoTradeReason

ET = ZoneInfo("America/New_York")


@pytest.fixture
def decision_engine():
    """Create decision engine with contract fixtures."""
    return DecisionEngine(contracts_path="src/trading_bot/contracts")


@pytest.fixture
def base_signals():
    """Baseline signals that pass all template conditions."""
    return {
        "session_phase_code": 2,  # MID_MORNING
        "vwap": Decimal("5000"),
        "atr14": Decimal("25.0"),
        "atr30": Decimal("12.0"),
        "spread_ticks": 1,
        "tr": Decimal("15.0"),
        # Used by friction model / shock checks in some builds
        "slippage_estimate_ticks": 1,
    }


@pytest.fixture
def base_state():
    """Baseline state that passes constitution gates."""
    return {
        "dvs": Decimal("0.85"),
        "eqs": Decimal("0.85"),
        "position": 0,
        "last_price": Decimal("4992.25"),  # strictly < -0.15% below VWAP
        "timestamp": datetime(2025, 1, 15, 10, 0, tzinfo=ET),  # MID_MORNING, tradable window
        "equity_usd": Decimal("1000.00"),  # Tier S by constitution
    }


@pytest.fixture
def base_risk_state():
    """Baseline risk state with no kill switch."""
    return {
        "kill_switch_active": False,
        "daily_pnl": Decimal("0"),
        "consecutive_losses": 0,
        "trades_today": 0,
        "last_entry_time": None,
    }


# ==========================================
# KILL SWITCH TESTS
# ==========================================

def test_kill_switch_blocks_all_trades(decision_engine, base_signals, base_state):
    """Test kill switch blocks trading regardless of other conditions."""
    risk_state = {
        "kill_switch_active": True,
        "kill_switch_reason": "DAILY_LOSS_LIMIT",
        "daily_pnl": Decimal("-150")
    }
    
    result = decision_engine.decide(base_signals, base_state, risk_state)
    
    assert result["action"] == "NO_TRADE"
    assert result["reason"] in (NoTradeReason.KILL_SWITCH_ACTIVE, NoTradeReason.DAILY_LOSS_LIMIT)
    assert "intent" not in result
    assert result["metadata"]["kill_switch_reason"] == "DAILY_LOSS_LIMIT"


# ==========================================
# CONSTITUTION GATE TESTS
# ==========================================

def test_dvs_below_threshold_blocks_trade(decision_engine, base_signals, base_risk_state):
    """Test DVS below constitution threshold blocks trade."""
    state = {
        "dvs": Decimal("0.60"),  # Below min_dvs_for_entry=0.80
        "eqs": Decimal("0.85"),
        "position": 0,
        "last_price": Decimal("4992.50"),
        "timestamp": datetime(2025, 1, 15, 10, 0, tzinfo=ET),
        "equity_usd": Decimal("1000.00"),
    }
    
    result = decision_engine.decide(base_signals, state, base_risk_state)
    
    assert result["action"] == "NO_TRADE"
    assert result["reason"] == NoTradeReason.DVS_TOO_LOW
    assert Decimal(str(result["metadata"]["dvs"])) == Decimal("0.60")


def test_eqs_below_threshold_blocks_trade(decision_engine, base_signals, base_risk_state):
    """Test EQS below constitution threshold blocks trade."""
    state = {
        "dvs": Decimal("0.85"),
        "eqs": Decimal("0.60"),  # Below min_eqs_for_entry=0.75
        "position": 0,
        "last_price": Decimal("4992.50"),
        "timestamp": datetime(2025, 1, 15, 10, 0, tzinfo=ET),
        "equity_usd": Decimal("1000.00"),
    }
    
    result = decision_engine.decide(base_signals, state, base_risk_state)
    
    assert result["action"] == "NO_TRADE"
    assert result["reason"] == NoTradeReason.EQS_TOO_LOW
    assert Decimal(str(result["metadata"]["eqs"])) == Decimal("0.60")


# ==========================================
# POSITION LIMIT TESTS
# ==========================================

def test_existing_position_blocks_new_trade(decision_engine, base_signals, base_risk_state):
    """Test existing position blocks new trade entry."""
    state = {
        "dvs": Decimal("0.85"),
        "eqs": Decimal("0.85"),
        "position": 1,  # Already in position
        "last_price": Decimal("4992.50"),
        "timestamp": datetime(2025, 1, 15, 10, 0, tzinfo=ET),
        "equity_usd": Decimal("1000.00"),
    }
    
    result = decision_engine.decide(base_signals, state, base_risk_state)
    
    assert result["action"] == "NO_TRADE"
    assert result["reason"] == NoTradeReason.IN_POSITION
    assert result["metadata"]["position"] == 1


# ==========================================
# TEMPLATE CONDITION TESTS
# ==========================================

def test_wrong_session_phase_blocks_trade(decision_engine, base_state, base_risk_state):
    """Test wrong session phase fails template entry conditions."""
    signals = {
        "session_phase_code": 3,  # LUNCH, not MID_MORNING
        "vwap": Decimal("5000"),
        "atr14": Decimal("25.0"),
        "spread_ticks": 1
    }
    
    result = decision_engine.decide(signals, base_state, base_risk_state)
    
    assert result["action"] == "NO_TRADE"
    assert result["reason"] in (NoTradeReason.SESSION_NOT_TRADABLE, NoTradeReason.CONDITION_NOT_MET)


def test_opening_no_trade_window_blocks_trade(decision_engine, base_signals, base_risk_state):
    """09:30-09:35 is a constitutional no-trade window (session.yaml)."""
    state = {
        "dvs": Decimal("0.85"),
        "eqs": Decimal("0.85"),
        "position": 0,
        "last_price": Decimal("4992.50"),
        "timestamp": datetime(2025, 1, 15, 9, 32, tzinfo=ET),
        "equity_usd": Decimal("1000.00"),
    }
    result = decision_engine.decide(base_signals, state, base_risk_state)
    assert result["action"] == "NO_TRADE"
    assert result["reason"] == NoTradeReason.SESSION_WINDOW_BLOCK


def test_price_not_below_vwap_blocks_trade(decision_engine, base_signals, base_risk_state):
    """Test price not sufficiently below VWAP blocks trade."""
    state = {
        "dvs": Decimal("0.85"),
        "eqs": Decimal("0.85"),
        "position": 0,
        "last_price": Decimal("5005.00"),  # Above VWAP
        "timestamp": datetime(2025, 1, 15, 10, 0, tzinfo=ET),
        "equity_usd": Decimal("1000.00"),
    }
    
    result = decision_engine.decide(base_signals, state, base_risk_state)
    
    assert result["action"] == "NO_TRADE"
    assert result["reason"] == NoTradeReason.CONDITION_NOT_MET


def test_atr_out_of_range_blocks_trade(decision_engine, base_state, base_risk_state):
    """Test ATR outside acceptable range blocks trade."""
    signals = {
        "session_phase_code": 2,
        "vwap": Decimal("5000"),
        "atr14": Decimal("1.0"),  # Too low (norm < 0.40%)
        "spread_ticks": 1
    }
    
    result = decision_engine.decide(signals, base_state, base_risk_state)
    
    assert result["action"] == "NO_TRADE"
    assert "ATR" in result["reason"] or "CONDITION_NOT_MET" in result["reason"]


def test_spread_too_wide_blocks_trade(decision_engine, base_state, base_risk_state):
    """Test spread exceeding limit blocks trade."""
    signals = {
        "session_phase_code": 2,
        "vwap": Decimal("5000"),
        "atr14": Decimal("10.0"),
        "spread_ticks": 5  # > 2 tick limit
    }
    
    result = decision_engine.decide(signals, base_state, base_risk_state)
    
    assert result["action"] == "NO_TRADE"
    assert result["reason"] in (NoTradeReason.SPREAD_TOO_WIDE, NoTradeReason.CONDITION_NOT_MET)


# ==========================================
# ORDER INTENT GENERATION TESTS
# ==========================================

def test_all_conditions_met_generates_order_intent(
    decision_engine, 
    base_signals, 
    base_state, 
    base_risk_state
):
    """Test all conditions met generates valid order intent."""
    result = decision_engine.decide(base_signals, base_state, base_risk_state)
    
    assert result["action"] == "ORDER_INTENT"
    assert "intent" in result
    
    intent = result["intent"]
    assert intent.direction in ("LONG", "SHORT")
    assert intent.contracts == 1  # constitution: max_position_contracts=1
    # Constitution must bound stop_ticks by tier + risk-derived limits.
    assert 1 <= intent.stop_ticks <= 10  # Tier S max_stop_distance_ticks=10
    assert intent.target_ticks > intent.stop_ticks  # asymmetric by design
    assert intent.strategy_id is not None


def test_order_intent_has_required_fields(
    decision_engine,
    base_signals,
    base_state,
    base_risk_state
):
    """Test order intent contains all required fields."""
    result = decision_engine.decide(base_signals, base_state, base_risk_state)
    
    assert result["action"] == "ORDER_INTENT"
    intent = result["intent"]
    
    # Validate OrderIntent dataclass fields
    assert hasattr(intent, "direction")
    assert hasattr(intent, "contracts")
    assert hasattr(intent, "entry_type")
    assert hasattr(intent, "stop_ticks")
    assert hasattr(intent, "target_ticks")
    assert hasattr(intent, "stop_order_type")
    assert hasattr(intent, "target_order_type")
    assert hasattr(intent, "strategy_id")
    assert hasattr(intent, "timestamp")
    assert hasattr(intent, "metadata")


def test_order_intent_includes_signal_snapshot(
    decision_engine,
    base_signals,
    base_state,
    base_risk_state
):
    """Test order intent metadata includes signal snapshot."""
    result = decision_engine.decide(base_signals, base_state, base_risk_state)
    
    assert result["action"] == "ORDER_INTENT"
    metadata = result["metadata"]
    
    assert "signals" in metadata
    signal_snapshot = metadata["signals"]
    assert "session_phase_code" in signal_snapshot
    assert "vwap" in signal_snapshot
    assert "atr14" in signal_snapshot


# ==========================================
# FAIL-CLOSED TESTS
# ==========================================

def test_missing_vwap_fails_closed(decision_engine, base_state, base_risk_state):
    """Test missing VWAP signal fails closed."""
    signals = {
        "session_phase_code": 2,
        "vwap": None,  # Missing VWAP
        "atr14": Decimal("10.0"),
        "spread_ticks": 1
    }
    
    result = decision_engine.decide(signals, base_state, base_risk_state)
    
    assert result["action"] == "NO_TRADE"
    assert result["reason"] == NoTradeReason.MISSING_REQUIRED_SIGNAL


def test_missing_atr_fails_closed(decision_engine, base_state, base_risk_state):
    """Test missing ATR signal fails closed."""
    signals = {
        "session_phase_code": 2,
        "vwap": Decimal("5000"),
        "atr14": None,  # Missing ATR
        "spread_ticks": 1
    }
    
    result = decision_engine.decide(signals, base_state, base_risk_state)
    
    assert result["action"] == "NO_TRADE"
    assert result["reason"] == NoTradeReason.MISSING_REQUIRED_SIGNAL


def test_missing_spread_fails_closed(decision_engine, base_state, base_risk_state):
    """Test missing spread signal fails closed."""
    signals = {
        "session_phase_code": 2,
        "vwap": Decimal("5000"),
        "atr14": Decimal("10.0"),
        "spread_ticks": None  # Missing spread
    }
    
    result = decision_engine.decide(signals, base_state, base_risk_state)
    
    assert result["action"] == "NO_TRADE"
    assert result["reason"] == NoTradeReason.MISSING_REQUIRED_SIGNAL


# ==========================================
# CONSTITUTION FREQUENCY LIMITS
# ==========================================

def test_max_trades_per_day_blocks_trade(decision_engine, base_signals, base_state):
    """Risk model: max_trades_per_day=10 (contract-aligned)."""
    risk_state = {
        "kill_switch_active": False,
        "daily_pnl": Decimal("0"),
        "consecutive_losses": 0,
        "trades_today": 10,
        "last_entry_time": datetime(2025, 1, 15, 10, 0, tzinfo=ET),
    }
    result = decision_engine.decide(base_signals, base_state, risk_state)
    assert result["action"] == "NO_TRADE"
    assert result["reason"] == NoTradeReason.MAX_TRADES_REACHED


def test_min_minutes_between_entries_blocks_trade(decision_engine, base_signals, base_state):
    """Cooling-off: min_minutes_between_entries=30 (engine-enforced)."""
    risk_state = {
        "kill_switch_active": False,
        "daily_pnl": Decimal("0"),
        "consecutive_losses": 0,
        "trades_today": 1,
        "last_entry_time": datetime(2025, 1, 15, 9, 45, tzinfo=ET),  # 15 minutes ago
    }
    state = dict(base_state)
    state["timestamp"] = datetime(2025, 1, 15, 10, 0, tzinfo=ET)
    result = decision_engine.decide(base_signals, state, risk_state)
    assert result["action"] == "NO_TRADE"
    assert result["reason"] == NoTradeReason.COOLDOWN_ACTIVE


def test_consecutive_losses_lockout_until_next_session(decision_engine, base_signals, base_state):
    """Risk model: after 3 consecutive losses -> lockout until next session."""
    risk_state = {
        "kill_switch_active": False,
        "daily_pnl": Decimal("0"),
        "consecutive_losses": 3,
        "trades_today": 0,
        "last_entry_time": None,
    }
    result = decision_engine.decide(base_signals, base_state, risk_state)
    assert result["action"] == "NO_TRADE"
    assert result["reason"] == NoTradeReason.CONSECUTIVE_LOSS_LOCKOUT


# ==========================================
# FRICTION GATE (HONEST MATH)
# ==========================================

def test_friction_gate_blocks_marginal_setups(decision_engine, base_state, base_risk_state):
    """
    Constitution: max_friction_share=0.30.
    If pessimistic_friction / expected_move_to_T1 > 0.30 -> no trade.
    """
    signals = {
        "session_phase_code": 2,
        "vwap": Decimal("5000"),
        "atr14": Decimal("25.0"),
        "atr30": Decimal("12.0"),
        "spread_ticks": 2,
        "tr": Decimal("15.0"),
        # Make execution expensive
        "slippage_estimate_ticks": 3,
    }
    state = dict(base_state)
    state["last_price"] = Decimal("4992.25")
    result = decision_engine.decide(signals, state, base_risk_state)
    assert result["action"] == "NO_TRADE"
    assert result["reason"] == NoTradeReason.FRICTION_TOO_HIGH
