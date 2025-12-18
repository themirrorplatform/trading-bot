from __future__ import annotations

from pathlib import Path
from trading_bot.core.config import load_contracts


def test_all_contracts_load_and_normalize():
    """Test that all contracts load and normalization succeeds."""
    contracts_dir = Path("src/trading_bot/contracts")
    contracts = load_contracts(str(contracts_dir))
    
    # Check all contracts are loaded
    assert "execution_contract.yaml" in contracts.docs
    assert "session.yaml" in contracts.docs
    assert "data_contract.yaml" in contracts.docs
    assert "strategy_templates.yaml" in contracts.docs
    assert "risk_model.yaml" in contracts.docs
    assert "calendar.yaml" in contracts.docs
    assert "constitution.yaml" in contracts.docs
    assert "market_instrument.yaml" in contracts.docs
    
    # Check normalization added lookup helpers
    assert "degradation_events_by_id" in contracts.docs["execution_contract.yaml"]["eqs"]
    assert "no_trade_windows_by_id" in contracts.docs["session.yaml"]
    assert "degradation_events_by_id" in contracts.docs["data_contract.yaml"]["dvs"]
    assert "strategy_templates_by_id" in contracts.docs["strategy_templates.yaml"]
    assert "triggers_by_id" in contracts.docs["risk_model.yaml"]["kill_switch"]
    assert "holiday_dates" in contracts.docs["calendar.yaml"]
    assert "half_day_dates" in contracts.docs["calendar.yaml"]
    
    # Check config hash is computed
    assert contracts.config_hash is not None
    assert len(contracts.config_hash) > 0
