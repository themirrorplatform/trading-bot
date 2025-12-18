from __future__ import annotations

from pathlib import Path
import yaml


def test_calendar_holidays_and_half_days_lists():
    path = Path("src/trading_bot/contracts/calendar.yaml")
    assert path.exists(), "calendar.yaml missing"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    holidays = data.get("holidays", [])
    assert isinstance(holidays, list), "holidays must be a list"
    half_days = data.get("half_days", [])
    assert isinstance(half_days, list), "half_days must be a list"
    
    # Check required fields
    for h in holidays:
        assert "date" in h, "holiday missing date"
        assert "name" in h, "holiday missing name"
    
    for h in half_days:
        assert "date" in h, "half_day missing date"
        assert "close_time" in h, "half_day missing close_time"
