from __future__ import annotations

from pathlib import Path
import yaml


def test_data_contract_degradation_events_list():
    path = Path("src/trading_bot/contracts/data_contract.yaml")
    assert path.exists(), "data_contract.yaml missing"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    dvs = data.get("dvs", {})
    events = dvs.get("degradation_events", [])
    assert isinstance(events, list), "dvs.degradation_events must be a list"
    ids = [e.get("id") for e in events]
    assert all(isinstance(i, str) and i.strip() for i in ids), "each event needs non-empty string id"
    assert len(set(ids)) == len(ids), "degradation event ids must be unique"
