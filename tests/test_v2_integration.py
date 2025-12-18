"""
Integration test for V2 engines: Signals → Beliefs → Decision

Tests the complete pipeline:
1. SignalEngineV2 computes all 28 signals
2. BeliefEngineV2 computes constraint likelihoods
3. DecisionEngineV2 applies capital tier gates and EUC scoring
"""

import pytest
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo

from src.trading_bot.engines.signals_v2 import SignalEngineV2
from src.trading_bot.engines.belief_v2 import BeliefEngineV2
from src.trading_bot.engines.decision_v2 import DecisionEngineV2, CapitalTier


ET = ZoneInfo("America/New_York")


def test_signal_engine_v2_computes_all_signals():
    """Test that SignalEngineV2 computes all 28 signals"""
    engine = SignalEngineV2()
    
    # Create test bar data
    timestamp = datetime(2025, 1, 15, 10, 0, tzinfo=ET)  # Opening phase
    
    # Warm up engine with 30 bars
    for i in range(30):
        ts = datetime(2025, 1, 15, 9, 30 + i, tzinfo=ET)
        result = engine.compute_signals(
            timestamp=ts,
            open_price=Decimal("5600.00") + Decimal(i) * Decimal("0.25"),
            high=Decimal("5600.50") + Decimal(i) * Decimal("0.25"),
            low=Decimal("5599.50") + Decimal(i) * Decimal("0.25"),
            close=Decimal("5600.25") + Decimal(i) * Decimal("0.25"),
            volume=1000 + i * 10,
            bid=Decimal("5600.00") + Decimal(i) * Decimal("0.25"),
            ask=Decimal("5600.25") + Decimal(i) * Decimal("0.25"),
            dvs=0.95,
            eqs=0.90
        )
    
    # Check that signals are computed
    assert result.vwap_z is not None or result.vwap_z == 0.0
    assert result.session_phase == 1  # Opening
    assert result.lunch_void_gate == 1.0  # Not lunch
    assert result.reliability.dvs_ok is True
    assert result.reliability.eqs_ok is True
    assert result.reliability.session_ok is True
    
    # Check price structure signals exist (may be None if warmup needed)
    assert hasattr(result, 'vwap_z')
    assert hasattr(result, 'atr_14_n')
    assert hasattr(result, 'range_compression')
    
    # Check volume signals
    assert hasattr(result, 'vol_z')
    assert hasattr(result, 'climax_bar_flag')
    
    # Check quality signals
    assert hasattr(result, 'spread_proxy_tickiness')
    assert result.spread_proxy_tickiness is not None


def test_belief_engine_v2_computes_likelihoods():
    """Test that BeliefEngineV2 computes constraint likelihoods"""
    engine = BeliefEngineV2()
    
    # Mock signal data
    signals = {
        "vwap_z": -1.5,  # Below VWAP (mean reversion signal)
        "range_compression": 0.6,  # Compressed range
        "vol_z": -0.5,  # Low volume
        "close_location_value": 0.8,  # High in range
        "friction_regime_index": 0.9,  # Good friction
        "dvs": 0.95,
        "session_phase": 1,  # Opening
    }
    
    beliefs = engine.compute_beliefs(
        signals=signals,
        session_phase=1,
        dvs=0.95,
        eqs=0.90
    )
    
    # Check that beliefs are computed for all constraints
    assert "F1" in beliefs  # VWAP MR
    assert "F3" in beliefs  # Failed break
    assert "F4" in beliefs  # Sweep reversal
    assert "F5" in beliefs  # Momentum
    assert "F6" in beliefs  # Noise filter
    
    # Check F1 (VWAP MR) should have high likelihood given signals
    f1_belief = beliefs["F1"]
    assert f1_belief.likelihood > 0.5  # Should favor mean reversion
    assert 0.0 <= f1_belief.applicability <= 1.0
    assert 0.0 <= f1_belief.stability <= 1.0
    
    # Check that effective likelihood is computed
    assert f1_belief.effective_likelihood == f1_belief.likelihood * f1_belief.applicability


def test_decision_engine_v2_capital_tier_gates():
    """Test capital tier gate enforcement"""
    engine = DecisionEngineV2()
    
    # Test tier S ($1000 equity)
    tier_s = engine.determine_capital_tier(Decimal("1000"))
    assert tier_s == CapitalTier.S
    
    allowed_s = engine.filter_templates_by_tier(tier_s)
    assert "K1" in allowed_s
    assert "K2" in allowed_s
    assert "K3" not in allowed_s  # Not allowed in tier S
    assert "K4" not in allowed_s
    
    # Test tier A ($5000 equity)
    tier_a = engine.determine_capital_tier(Decimal("5000"))
    assert tier_a == CapitalTier.A
    
    allowed_a = engine.filter_templates_by_tier(tier_a)
    assert "K1" in allowed_a
    assert "K2" in allowed_a
    assert "K3" in allowed_a  # Now allowed
    assert "K4" not in allowed_a  # Still not allowed
    
    # Test tier B ($10000 equity)
    tier_b = engine.determine_capital_tier(Decimal("10000"))
    assert tier_b == CapitalTier.B
    
    allowed_b = engine.filter_templates_by_tier(tier_b)
    assert "K1" in allowed_b
    assert "K2" in allowed_b
    assert "K3" in allowed_b
    assert "K4" in allowed_b  # All templates allowed


def test_decision_engine_v2_euc_scoring():
    """Test Edge-Uncertainty-Cost scoring"""
    engine = DecisionEngineV2()
    
    # Get template
    template = engine.templates["K1"]
    
    # Test with good conditions
    euc_good = engine.compute_euc_score(
        template=template,
        belief_likelihood=0.80,  # High belief
        belief_stability=0.10,  # Low stability (good)
        dvs=0.95,  # High DVS
        eqs=0.90,  # High EQS
        friction_usd=Decimal("9.00"),  # Base friction
        atr_14=Decimal("3.00")
    )
    
    assert euc_good.edge > 0.0
    assert euc_good.uncertainty < 0.5  # Should be low
    assert euc_good.cost < 0.5  # Should be low
    assert euc_good.total_score > 0.0  # Positive total score
    
    # Test with bad conditions
    euc_bad = engine.compute_euc_score(
        template=template,
        belief_likelihood=0.50,  # Low belief
        belief_stability=0.40,  # High stability (bad)
        dvs=0.70,  # Lower DVS
        eqs=0.65,  # Lower EQS
        friction_usd=Decimal("15.00"),  # High friction
        atr_14=Decimal("1.50")  # Low ATR (high cost ratio)
    )
    
    assert euc_bad.uncertainty > euc_good.uncertainty
    assert euc_bad.cost > euc_good.cost
    assert euc_bad.total_score < euc_good.total_score


def test_full_pipeline_integration():
    """Test complete pipeline: Signals → Beliefs → Decision"""
    # Initialize engines
    signal_engine = SignalEngineV2()
    belief_engine = BeliefEngineV2()
    decision_engine = DecisionEngineV2()
    
    # Generate signal data
    timestamp = datetime(2025, 1, 15, 10, 30, tzinfo=ET)
    
    # Warm up signal engine
    for i in range(30):
        ts = datetime(2025, 1, 15, 9, 30 + i, tzinfo=ET)
        signal_engine.compute_signals(
            timestamp=ts,
            open_price=Decimal("5600.00"),
            high=Decimal("5600.50"),
            low=Decimal("5599.50"),
            close=Decimal("5600.25"),
            volume=1000,
            bid=Decimal("5600.00"),
            ask=Decimal("5600.25"),
            dvs=0.95,
            eqs=0.90
        )
    
    # Compute signals for current bar
    signals_output = signal_engine.compute_signals(
        timestamp=timestamp,
        open_price=Decimal("5600.00"),
        high=Decimal("5600.75"),
        low=Decimal("5599.75"),
        close=Decimal("5600.50"),
        volume=1200,
        bid=Decimal("5600.25"),
        ask=Decimal("5600.50"),
        dvs=0.95,
        eqs=0.90
    )
    
    # Convert signals to dict for belief engine
    signals_dict = {
        "vwap_z": signals_output.vwap_z,
        "vwap_slope": signals_output.vwap_slope,
        "range_compression": signals_output.range_compression,
        "vol_z": signals_output.vol_z,
        "close_location_value": signals_output.close_location_value,
        "friction_regime_index": signals_output.friction_regime_index,
        "dvs": signals_output.dvs,
        "eqs": 0.90,
        "session_phase": signals_output.session_phase,
        "lunch_void_gate": signals_output.lunch_void_gate,
        "spread_proxy_tickiness": signals_output.spread_proxy_tickiness,
        "slippage_risk_proxy": signals_output.slippage_risk_proxy,
        "atr_14_n": signals_output.atr_14_n,
        # Add more signals as needed
    }
    
    # Compute beliefs
    beliefs = belief_engine.compute_beliefs(
        signals=signals_dict,
        session_phase=signals_output.session_phase,
        dvs=signals_output.dvs,
        eqs=0.90
    )
    
    # Make decision
    decision = decision_engine.decide(
        equity=Decimal("5000"),  # Tier A
        beliefs=beliefs,
        signals=signals_dict,
        state={"timestamp": timestamp, "eqs": 0.90},
        risk_state={"kill_switch_active": False}
    )
    
    # Check decision structure
    assert decision.action in ["NO_TRADE", "ORDER_INTENT"]
    assert decision.timestamp == timestamp
    assert "tier" in decision.metadata
    
    # If trade, check order intent structure
    if decision.action == "ORDER_INTENT":
        assert decision.order_intent is not None
        assert "direction" in decision.order_intent
        assert "contracts" in decision.order_intent
        assert decision.order_intent["contracts"] == 1
        assert decision.order_intent["entry_type"] == "LIMIT"  # No market orders


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
