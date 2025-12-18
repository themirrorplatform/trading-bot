from __future__ import annotations

from pathlib import Path
import yaml


def test_strategy_templates_is_list():
    path = Path("src/trading_bot/contracts/strategy_templates.yaml")
    assert path.exists(), "strategy_templates.yaml missing"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    templates = data.get("strategy_templates", [])
    assert isinstance(templates, list), "strategy_templates must be a list"
    ids = [t.get("id") for t in templates]
    assert all(isinstance(i, str) and i.strip() for i in ids), "each template needs non-empty string id"
    assert len(set(ids)) == len(ids), "template ids must be unique"
