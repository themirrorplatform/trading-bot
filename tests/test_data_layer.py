"""
Tests for data layer: bar validation, DVS evaluation, session/calendar gating.
"""

import pytest
from datetime import datetime, time
from decimal import Decimal
from pathlib import Path

from src.trading_bot.engines.data_layer import DataLayer, Bar
from src.trading_bot.core.config import load_contracts


@pytest.fixture
def contracts():
    """Load contracts for data layer tests."""
    contracts_dir = Path("src/trading_bot/contracts")
    return load_contracts(str(contracts_dir))


@pytest.fixture
def data_layer(contracts):
    """Create DataLayer instance."""
    return DataLayer(contracts)


def test_bar_validation_pass(data_layer):
    """Test valid bar passes all checks."""
    bar = Bar(
        timestamp=datetime(2025, 1, 15, 10, 0),
        open=Decimal("5000.00"),
        high=Decimal("5001.00"),
        low=Decimal("4999.50"),
        close=Decimal("5000.50"),
        volume=1000,
        symbol="MES"
    )
    
    report = data_layer.validate_bar(bar)
    assert report.bar_valid is True
    assert len(report.rejected_checks) == 0
    assert report.dvs >= 0.0 and report.dvs <= 1.0


def test_bar_validation_fail_ohlc(data_layer):
    """Test bar with invalid OHLC fails."""
    bar = Bar(
        timestamp=datetime(2025, 1, 15, 10, 0),
        open=Decimal("5000.00"),
        high=Decimal("4999.00"),  # high < open (invalid)
        low=Decimal("4999.50"),
        close=Decimal("5000.50"),
        volume=1000,
        symbol="MES"
    )
    
    report = data_layer.validate_bar(bar)
    assert report.bar_valid is False
    assert "ohlc_open_range" in report.rejected_checks
    assert report.dvs == 0.0  # Failed bar -> DVS = 0


def test_bar_validation_fail_volume(data_layer):
    """Test bar with negative volume fails."""
    bar = Bar(
        timestamp=datetime(2025, 1, 15, 10, 0),
        open=Decimal("5000.00"),
        high=Decimal("5001.00"),
        low=Decimal("4999.50"),
        close=Decimal("5000.50"),
        volume=-100,  # negative volume (invalid)
        symbol="MES"
    )
    
    report = data_layer.validate_bar(bar)
    assert report.bar_valid is False
    assert "volume_negative" in report.rejected_checks
    assert report.dvs == 0.0


def test_trading_allowed_normal_hours(data_layer):
    """Test trading allowed during normal session."""
    # 2025-01-15 10:00 ET (not a holiday, not in no-trade window)
    current_time = datetime(2025, 1, 15, 10, 0)
    dvs = 0.80
    
    allowed = data_layer.is_trading_allowed(current_time, dvs)
    assert allowed is True


def test_trading_blocked_holiday(data_layer):
    """Test trading blocked on market holiday."""
    # 2025-01-01 (New Year's Day - holiday)
    current_time = datetime(2025, 1, 1, 10, 0)
    dvs = 0.80
    
    allowed = data_layer.is_trading_allowed(current_time, dvs)
    assert allowed is False


def test_trading_blocked_opening_window(data_layer):
    """Test trading blocked during opening no-trade window (09:30-09:35)."""
    # 2025-01-15 09:32 ET (in OPENING_BLOCK)
    current_time = datetime(2025, 1, 15, 9, 32)
    dvs = 0.80
    
    allowed = data_layer.is_trading_allowed(current_time, dvs)
    assert allowed is False


def test_trading_blocked_lunch_window(data_layer):
    """Test trading blocked during lunch no-trade window (11:30-13:30)."""
    # 2025-01-15 12:00 ET (in LUNCH_BLOCK)
    current_time = datetime(2025, 1, 15, 12, 0)
    dvs = 0.80
    
    allowed = data_layer.is_trading_allowed(current_time, dvs)
    assert allowed is False


def test_trading_blocked_low_dvs(data_layer):
    """Test trading blocked when DVS below threshold."""
    # 2025-01-15 10:00 ET (normal hours but DVS too low)
    current_time = datetime(2025, 1, 15, 10, 0)
    dvs = 0.50  # Below 0.70 threshold
    
    allowed = data_layer.is_trading_allowed(current_time, dvs)
    assert allowed is False


def test_trading_allowed_after_opening_window(data_layer):
    """Test trading allowed after opening window ends (09:35)."""
    # 2025-01-15 09:36 ET (just after OPENING_BLOCK)
    current_time = datetime(2025, 1, 15, 9, 36)
    dvs = 0.80
    
    allowed = data_layer.is_trading_allowed(current_time, dvs)
    assert allowed is True


def test_half_day_early_close(data_layer):
    """Test trading blocked after half-day close (e.g., 2025-07-03 after 13:00)."""
    # 2025-07-03 13:05 ET (after half-day close at 13:00)
    current_time = datetime(2025, 7, 3, 13, 5)
    dvs = 0.80
    
    allowed = data_layer.is_trading_allowed(current_time, dvs)
    assert allowed is False


def test_dvs_extraction_spread(data_layer):
    """Test DVS event extraction computes spread correctly."""
    bar = Bar(
        timestamp=datetime(2025, 1, 15, 10, 0),
        open=Decimal("5000.00"),
        high=Decimal("5010.00"),
        low=Decimal("4990.00"),
        close=Decimal("5000.00"),
        volume=1000,
        symbol="MES"
    )
    
    observed = data_layer._extract_dvs_events(bar)
    
    # Spread = (5010 - 4990) / 5000 * 10000 = 40 bps
    assert "spread_bps" in observed
    assert abs(observed["spread_bps"] - 40.0) < 0.01
    
    # Volume
    assert observed["volume"] == 1000
