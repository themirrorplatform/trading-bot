"""
Tests for risk engine: per-trade, per-day, drawdown, kill-switch enforcement.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from src.trading_bot.engines.risk_engine import RiskEngine, RiskState
from src.trading_bot.core.config import load_contracts


@pytest.fixture
def contracts():
    """Load contracts for risk engine tests."""
    contracts_dir = Path("src/trading_bot/contracts")
    return load_contracts(str(contracts_dir))


@pytest.fixture
def risk_engine(contracts):
    """Create RiskEngine instance."""
    return RiskEngine(contracts, tick_value=Decimal("1.25"))


def test_pre_trade_check_pass(risk_engine):
    """Test pre-trade checks pass with valid conditions."""
    result = risk_engine.check_pre_trade(
        dvs=0.80,
        eqs=0.80,
        intended_position_size=1,
        entry_price=Decimal("5000.00"),
        stop_price=Decimal("4999.00")  # 4 tick stop = $5 risk
    )
    
    assert result.passed is True
    assert len(result.failed_checks) == 0


def test_pre_trade_check_fail_dvs(risk_engine):
    """Test pre-trade checks fail when DVS too low."""
    result = risk_engine.check_pre_trade(
        dvs=0.50,  # Below 0.75 threshold
        eqs=0.80,
        intended_position_size=1,
        entry_price=Decimal("5000.00"),
        stop_price=Decimal("4999.00")
    )
    
    assert result.passed is False
    assert any("dvs_too_low" in check for check in result.failed_checks)


def test_pre_trade_check_fail_eqs(risk_engine):
    """Test pre-trade checks fail when EQS too low."""
    result = risk_engine.check_pre_trade(
        dvs=0.80,
        eqs=0.50,  # Below 0.75 threshold
        intended_position_size=1,
        entry_price=Decimal("5000.00"),
        stop_price=Decimal("4999.00")
    )
    
    assert result.passed is False
    assert any("eqs_too_low" in check for check in result.failed_checks)


def test_pre_trade_check_fail_risk_too_high(risk_engine):
    """Test pre-trade checks fail when risk exceeds $5 limit."""
    result = risk_engine.check_pre_trade(
        dvs=0.80,
        eqs=0.80,
        intended_position_size=1,
        entry_price=Decimal("5000.00"),
        stop_price=Decimal("4994.00")  # 24 ticks = $30 risk (exceeds $5)
    )
    
    assert result.passed is False
    assert any("per_trade_risk" in check for check in result.failed_checks)


def test_pre_trade_check_fail_daily_limit(risk_engine):
    """Test pre-trade checks fail when daily trade limit reached."""
    # Simulate 10 trades already executed
    risk_engine.state.daily_trades = 10
    
    result = risk_engine.check_pre_trade(
        dvs=0.80,
        eqs=0.80,
        intended_position_size=1,
        entry_price=Decimal("5000.00"),
        stop_price=Decimal("4999.00")
    )
    
    assert result.passed is False
    assert "daily_trade_limit" in result.failed_checks


def test_pre_trade_check_fail_kill_switch(risk_engine):
    """Test pre-trade checks fail when kill switch active."""
    risk_engine.trigger_kill_switch("test_trigger")
    
    result = risk_engine.check_pre_trade(
        dvs=0.80,
        eqs=0.80,
        intended_position_size=1,
        entry_price=Decimal("5000.00"),
        stop_price=Decimal("4999.00")
    )
    
    assert result.passed is False
    assert "kill_switch_active" in result.failed_checks


def test_in_trade_check_pass(risk_engine):
    """Test in-trade checks pass with valid conditions."""
    result = risk_engine.check_in_trade(
        dvs=0.80,
        eqs=0.80,
        current_pnl=Decimal("-2.00")
    )
    
    assert result.passed is True


def test_in_trade_check_fail_dvs_kill(risk_engine):
    """Test in-trade checks fail when DVS drops below kill-switch threshold."""
    result = risk_engine.check_in_trade(
        dvs=0.25,  # Below 0.30 kill-switch
        eqs=0.80,
        current_pnl=Decimal("-2.00")
    )
    
    assert result.passed is False
    assert any("dvs_kill_switch" in check for check in result.failed_checks)


def test_in_trade_check_fail_eqs_kill(risk_engine):
    """Test in-trade checks fail when EQS drops below kill-switch threshold."""
    result = risk_engine.check_in_trade(
        dvs=0.80,
        eqs=0.25,  # Below 0.30 kill-switch
        current_pnl=Decimal("-2.00")
    )
    
    assert result.passed is False
    assert any("eqs_kill_switch" in check for check in result.failed_checks)


def test_in_trade_check_fail_daily_loss(risk_engine):
    """Test in-trade checks fail when daily loss exceeds limit."""
    # Simulate prior losses bringing us near limit
    risk_engine.state.daily_pnl = Decimal("-45.00")
    
    result = risk_engine.check_in_trade(
        dvs=0.80,
        eqs=0.80,
        current_pnl=Decimal("-10.00")  # Would push total to -$55, exceeds -$50 limit
    )
    
    assert result.passed is False
    assert any("daily_loss_limit" in check for check in result.failed_checks)


def test_update_on_trade_close_win(risk_engine):
    """Test risk state update on winning trade."""
    risk_engine.update_on_trade_close(Decimal("10.00"))
    
    assert risk_engine.state.daily_pnl == Decimal("10.00")
    assert risk_engine.state.daily_trades == 1
    assert risk_engine.state.consecutive_wins == 1
    assert risk_engine.state.consecutive_losses == 0


def test_update_on_trade_close_loss(risk_engine):
    """Test risk state update on losing trade."""
    risk_engine.update_on_trade_close(Decimal("-5.00"))
    
    assert risk_engine.state.daily_pnl == Decimal("-5.00")
    assert risk_engine.state.daily_trades == 1
    assert risk_engine.state.consecutive_wins == 0
    assert risk_engine.state.consecutive_losses == 1


def test_consecutive_losses_trigger_kill_switch(risk_engine):
    """Test kill switch triggers on 3 consecutive losses."""
    # Trade 1: loss
    risk_engine.update_on_trade_close(Decimal("-5.00"))
    assert risk_engine.state.kill_switch_active is False
    
    # Trade 2: loss
    risk_engine.update_on_trade_close(Decimal("-5.00"))
    assert risk_engine.state.kill_switch_active is False
    
    # Trade 3: loss (should trigger)
    risk_engine.update_on_trade_close(Decimal("-5.00"))
    assert risk_engine.state.kill_switch_active is True
    assert "consecutive_losses" in risk_engine.state.kill_switch_reason
    assert risk_engine.state.pause_until is not None


def test_daily_loss_trigger_kill_switch(risk_engine):
    """Test kill switch triggers on -$50 daily loss."""
    # Simulate losses totaling -$50
    risk_engine.update_on_trade_close(Decimal("-20.00"))
    assert risk_engine.state.kill_switch_active is False
    
    risk_engine.update_on_trade_close(Decimal("-20.00"))
    assert risk_engine.state.kill_switch_active is False
    
    risk_engine.update_on_trade_close(Decimal("-10.00"))
    # Should trigger at -$50
    assert risk_engine.state.kill_switch_active is True
    assert "daily_loss" in risk_engine.state.kill_switch_reason


def test_drawdown_tracking(risk_engine):
    """Test drawdown tracking updates correctly."""
    # Win: +$10 (peak = $10)
    risk_engine.update_on_trade_close(Decimal("10.00"))
    assert risk_engine.state.peak_equity == Decimal("10.00")
    assert risk_engine.state.max_drawdown == Decimal("0")
    
    # Win: +$5 (peak = $15)
    risk_engine.update_on_trade_close(Decimal("5.00"))
    assert risk_engine.state.peak_equity == Decimal("15.00")
    
    # Loss: -$8 (equity = $7, drawdown = $8)
    risk_engine.update_on_trade_close(Decimal("-8.00"))
    assert risk_engine.state.daily_pnl == Decimal("7.00")
    assert risk_engine.state.max_drawdown == Decimal("8.00")
    
    # Loss: -$5 (equity = $2, drawdown = $13)
    risk_engine.update_on_trade_close(Decimal("-5.00"))
    assert risk_engine.state.max_drawdown == Decimal("13.00")


def test_reset_daily_state(risk_engine):
    """Test daily state reset clears all counters."""
    # Build up some state
    risk_engine.update_on_trade_close(Decimal("-10.00"))
    risk_engine.update_on_trade_close(Decimal("-10.00"))
    risk_engine.trigger_kill_switch("test")
    
    # Reset
    risk_engine.reset_daily_state()
    
    # Verify cleared
    assert risk_engine.state.daily_pnl == Decimal("0")
    assert risk_engine.state.daily_trades == 0
    assert risk_engine.state.consecutive_wins == 0
    assert risk_engine.state.consecutive_losses == 0
    assert risk_engine.state.max_drawdown == Decimal("0")
    assert risk_engine.state.kill_switch_active is False
    assert risk_engine.state.pause_until is None


def test_position_tracking(risk_engine):
    """Test position open/close tracking."""
    # Open position
    risk_engine.open_position(1, Decimal("5000.00"))
    assert risk_engine.state.net_position == 1
    assert risk_engine.state.position_entry_price == Decimal("5000.00")
    
    # Close position
    risk_engine.close_position()
    assert risk_engine.state.net_position == 0
    assert risk_engine.state.position_entry_price is None
