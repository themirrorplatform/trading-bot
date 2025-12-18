from __future__ import annotations

from pathlib import Path
import yaml


def test_risk_model_kill_switch_triggers_list():
    path = Path("src/trading_bot/contracts/risk_model.yaml")
    assert path.exists(), "risk_model.yaml missing"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    kill_switch = data.get("kill_switch", {})
    triggers = kill_switch.get("triggers", [])
    assert isinstance(triggers, list), "kill_switch.triggers must be a list"
    ids = [t.get("id") for t in triggers]
    assert all(isinstance(i, str) and i.strip() for i in ids), "each trigger needs non-empty string id"
    assert len(set(ids)) == len(ids), "trigger ids must be unique"
