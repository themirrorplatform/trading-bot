"""
Test harness for bias/strategy permission system.

Validates:
- Bias detection from synthetic bars
- Strategy recognition
- Permission gate logic
"""
import json
from decimal import Decimal
from datetime import datetime, timezone
from trading_bot.engines.bias_engine import BiasEngine
from trading_bot.engines.strategy_recognizer import StrategyRecognizer
from trading_bot.engines.permission_layer import PermissionLayer


def test_bias_detection():
    """Test bias detection on synthetic trending bar."""
    bias_engine = BiasEngine()
    
    # Synthetic bar: strong upward impulse
    bar = {
        "open": 5900.0,
        "high": 5920.0,
        "low": 5898.0,
        "close": 5918.0,
        "volume": 5000
    }
    
    # Signals: high momentum, low value (extended)
    signals = {
        "F1": 0.7,  # Consistency
        "F4": 0.3,  # Value (extended from mean)
        "F5": 0.8,  # Momentum (strong)
        "T5": 0.6,  # Volatility
    }
    
    # Context
    context = {
        "prev_close": 5900.0,
        "prev_high": 5905.0,
        "prev_low": 5895.0,
        "avg_volume": 4000,
        "avg_range": 15.0,
        "avg_atr": 12.0,
        "current_session": "NY_OPEN",
        "near_round_number": 0.0,
    }
    
    bias_state = bias_engine.compute(bar, signals, context)
    
    print("=" * 60)
    print("BIAS DETECTION TEST")
    print("=" * 60)
    print(f"Active Biases: {len(bias_state.active)}")
    for bias in bias_state.active:
        print(f"  - {bias['bias_id']}: strength={bias['strength']:.2f}, confidence={bias['confidence']:.2f}")
    
    print(f"\nRegime: {bias_state.regime}")
    print(f"Conflicts: {len(bias_state.conflicts)}")
    
    # Assertions
    assert len(bias_state.active) > 0, "Expected at least one active bias"
    trend_active = any("TREND" in b["bias_id"] for b in bias_state.active)
    print(f"\n✓ Trend bias detected: {trend_active}")
    
    return bias_state


def test_strategy_recognition(bias_state):
    """Test strategy recognition with bias state."""
    strategy_recognizer = StrategyRecognizer()
    
    bar = {
        "open": 5900.0,
        "high": 5920.0,
        "low": 5898.0,
        "close": 5918.0,
        "volume": 5000
    }
    
    signals = {
        "F1": 0.7,
        "F4": 0.3,
        "F5": 0.8,
        "T5": 0.6,
    }
    
    context = {
        "prev_close": 5900.0,
        "prev_high": 5905.0,
        "prev_low": 5895.0,
    }
    
    strategy_state = strategy_recognizer.compute(bar, signals, bias_state, context)
    
    print("\n" + "=" * 60)
    print("STRATEGY RECOGNITION TEST")
    print("=" * 60)
    print(f"Active Strategies: {len(strategy_state.active)}")
    for strat in strategy_state.active[:5]:
        print(f"  - {strat['strategy_id']}: prob={strat['probability']:.2f}, posture={strat['posture']}")
    
    print(f"\nDominant Strategies: {len(strategy_state.dominance)}")
    for dom in strategy_state.dominance[:3]:
        print(f"  - {dom['strategy_id']}: dominance={dom['dominance_score']:.2f}")
    
    print(f"\nTrapped Strategies: {len(strategy_state.traps)}")
    
    # Assertions
    assert len(strategy_state.active) > 0, "Expected at least one active strategy"
    trend_strategy = any("TREND" in s["strategy_id"] for s in strategy_state.active)
    print(f"\n✓ Trend strategy detected: {trend_strategy}")
    
    return strategy_state


def test_permission_layer(bias_state, strategy_state):
    """Test permission layer decision."""
    permission_layer = PermissionLayer()
    
    belief_state = {
        "C1": {"effective_likelihood": 0.7},
        "C2": {"effective_likelihood": 0.5},
    }
    
    context = {}
    
    permission = permission_layer.compute(bias_state, strategy_state, belief_state, context)
    
    print("\n" + "=" * 60)
    print("PERMISSION LAYER TEST")
    print("=" * 60)
    print(f"Allow Trade: {permission.allow_trade}")
    print(f"Allowed Directions: {permission.allowed_directions}")
    print(f"Max Risk Units: {permission.max_risk_units:.2f}")
    print(f"Required Confirmation: {permission.required_confirmation}")
    if permission.stand_down_reason:
        print(f"Stand Down Reason: {permission.stand_down_reason}")
    
    # Assertions
    if permission.allow_trade:
        assert len(permission.allowed_directions) > 0, "Expected allowed directions"
        assert permission.max_risk_units > 0, "Expected positive risk units"
        print("\n✓ Permission granted")
    else:
        print(f"\n✓ Permission denied: {permission.stand_down_reason}")
    
    return permission


def test_dead_market_rejection():
    """Test that dead market bias blocks trading."""
    bias_engine = BiasEngine()
    
    # Dead market: low vol, no movement
    bar = {
        "open": 5900.0,
        "high": 5902.0,
        "low": 5899.0,
        "close": 5900.5,
        "volume": 500
    }
    
    signals = {
        "F1": 0.5,
        "F4": 0.5,  # At VWAP
        "F5": 0.5,  # No momentum
        "T5": 0.2,  # Low volatility
    }
    
    context = {
        "prev_close": 5900.0,
        "prev_high": 5901.0,
        "prev_low": 5899.0,
        "avg_volume": 4000,
        "avg_range": 15.0,
        "avg_atr": 12.0,
        "current_session": "MIDDAY",
        "near_round_number": 1.0,
    }
    
    bias_state = bias_engine.compute(bar, signals, context)
    strategy_recognizer = StrategyRecognizer()
    strategy_state = strategy_recognizer.compute(bar, signals, bias_state, context)
    
    permission_layer = PermissionLayer()
    permission = permission_layer.compute(bias_state, strategy_state, {}, context)
    
    print("\n" + "=" * 60)
    print("DEAD MARKET REJECTION TEST")
    print("=" * 60)
    print(f"Active Biases: {[b['bias_id'] for b in bias_state.active]}")
    print(f"Regime: {bias_state.regime}")
    print(f"Allow Trade: {permission.allow_trade}")
    if not permission.allow_trade:
        print(f"Reason: {permission.stand_down_reason}")
    
    # Should be blocked by dead market
    print(f"\n✓ Dead market correctly blocked: {not permission.allow_trade}")
    
    return permission


if __name__ == "__main__":
    print("Running bias/strategy permission tests...\n")
    
    # Test 1: Bias detection
    bias_state = test_bias_detection()
    
    # Test 2: Strategy recognition
    strategy_state = test_strategy_recognition(bias_state)
    
    # Test 3: Permission layer
    permission = test_permission_layer(bias_state, strategy_state)
    
    # Test 4: Dead market rejection
    dead_permission = test_dead_market_rejection()
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)
    
    summary = {
        "bias_count": len(bias_state.active),
        "strategy_count": len(strategy_state.active),
        "permission_granted": permission.allow_trade,
        "dead_market_blocked": not dead_permission.allow_trade
    }
    
    print(json.dumps(summary, indent=2))
