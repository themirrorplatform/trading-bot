from __future__ import annotations

from pathlib import Path
import yaml


def test_execution_contract_degradation_events_is_list():
    path = Path("src/trading_bot/contracts/execution_contract.yaml")
    assert path.exists(), "execution_contract.yaml missing"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    eqs = (data or {}).get("eqs", {})
    events = eqs.get("degradation_events")
    assert isinstance(events, list), "eqs.degradation_events must be a list"
    ids = [ev.get("id") for ev in events]
    assert all(isinstance(i, str) and i.strip() for i in ids), "each event needs non-empty string id"
    assert len(set(ids)) == len(ids), "degradation event ids must be unique"
