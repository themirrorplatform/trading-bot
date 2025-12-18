from __future__ import annotations

from pathlib import Path
import yaml


def test_session_no_trade_windows_list():
    path = Path("src/trading_bot/contracts/session.yaml")
    assert path.exists(), "session.yaml missing"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    windows = data.get("no_trade_windows", [])
    assert isinstance(windows, list), "no_trade_windows must be a list"
    ids = [w.get("id") for w in windows]
    assert all(isinstance(i, str) and i.strip() for i in ids), "each window needs non-empty string id"
    assert len(set(ids)) == len(ids), "window ids must be unique"
