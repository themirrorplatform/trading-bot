from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .types import sha256_hex, stable_json

CONTRACT_FILES = [
    "constitution.yaml",
    "session.yaml",
    "market_instrument.yaml",
    "data_contract.yaml",
    "execution_contract.yaml",
    "strategy_templates.yaml",
    "risk_model.yaml",
    "observability.yaml",
    "state_contract.yaml",
    "calendar.yaml",
]

@dataclass(frozen=True)
class Contracts:
    root: Path
    docs: Dict[str, Dict[str, Any]]
    config_hash: str

def load_yaml_contract(contracts_dir: str, filename: str) -> Dict[str, Any]:
    """Load a single YAML contract file.
    
    Args:
        contracts_dir: Directory containing contract YAML files
        filename: Name of the YAML file to load (e.g., "strategy_templates.yaml")
    
    Returns:
        Parsed YAML contract as a dictionary
    """
    root = Path(contracts_dir)
    contract_path = root / filename
    with contract_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_contracts(contracts_dir: str) -> Contracts:
    root = Path(contracts_dir)
    docs: Dict[str, Dict[str, Any]] = {}
    for fn in CONTRACT_FILES:
        p = root / fn
        with p.open("r", encoding="utf-8") as f:
            docs[fn] = yaml.safe_load(f)
    
    # Normalize all contracts
    if "execution_contract.yaml" in docs:
        docs["execution_contract.yaml"] = normalize_execution_contract(docs["execution_contract.yaml"])
    if "session.yaml" in docs:
        docs["session.yaml"] = normalize_session_contract(docs["session.yaml"])
    if "data_contract.yaml" in docs:
        docs["data_contract.yaml"] = normalize_data_contract(docs["data_contract.yaml"])
    if "strategy_templates.yaml" in docs:
        docs["strategy_templates.yaml"] = normalize_strategy_templates(docs["strategy_templates.yaml"])
    if "risk_model.yaml" in docs:
        docs["risk_model.yaml"] = normalize_risk_model(docs["risk_model.yaml"])
    if "calendar.yaml" in docs:
        docs["calendar.yaml"] = normalize_calendar(docs["calendar.yaml"])
    
    # Hash normalized representation (stable_json)
    config_hash = sha256_hex(stable_json(docs))
    return Contracts(root=root, docs=docs, config_hash=config_hash)


def _require(condition: bool, msg: str) -> None:
    """Fail-closed helper for contract validation."""
    if not condition:
        raise ValueError(msg)


def normalize_execution_contract(execution_contract: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize execution_contract into a deterministic, validated shape.

    Expectations:
    - execution_contract["eqs"]["degradation_events"] is a LIST of dicts
    - each event has a unique, non-empty string id
    - preserves list order while also exposing by-id lookup helpers
    """

    if not isinstance(execution_contract, dict):
        raise ValueError("execution_contract must be a mapping")

    eqs = execution_contract.get("eqs", {})
    _require(isinstance(eqs, dict), "execution_contract.eqs must be a mapping")

    events = eqs.get("degradation_events", [])
    _require(isinstance(events, list), "execution_contract.eqs.degradation_events must be a list")

    by_id: Dict[str, Any] = {}
    ids: List[str] = []
    for idx, ev in enumerate(events):
        _require(isinstance(ev, dict), f"execution_contract.eqs.degradation_events[{idx}] must be an object")
        _require("id" in ev and isinstance(ev["id"], str) and ev["id"].strip(),
                 f"execution_contract.eqs.degradation_events[{idx}] missing non-empty 'id'")
        _require("condition" in ev, f"execution_contract.eqs.degradation_events[{idx}] missing 'condition'")

        ev_id = ev["id"].strip()
        _require(ev_id not in by_id, f"duplicate execution_contract.eqs.degradation_events id: {ev_id}")
        by_id[ev_id] = ev
        ids.append(ev_id)

    eqs["degradation_events"] = events
    eqs["degradation_events_by_id"] = by_id
    eqs["degradation_event_ids"] = ids
    execution_contract["eqs"] = eqs
    return execution_contract


def normalize_session_contract(session: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize session contract: validate no-trade windows list."""
    _require(isinstance(session, dict), "session must be a mapping")
    
    no_trade_windows = session.get("no_trade_windows", [])
    _require(isinstance(no_trade_windows, list), "session.no_trade_windows must be a list")
    
    by_id: Dict[str, Any] = {}
    for idx, window in enumerate(no_trade_windows):
        _require(isinstance(window, dict), f"session.no_trade_windows[{idx}] must be an object")
        _require("id" in window and isinstance(window["id"], str) and window["id"].strip(),
                 f"session.no_trade_windows[{idx}] missing non-empty 'id'")
        win_id = window["id"].strip()
        _require(win_id not in by_id, f"duplicate session.no_trade_windows id: {win_id}")
        by_id[win_id] = window
    
    session["no_trade_windows_by_id"] = by_id
    return session


def normalize_data_contract(data_contract: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize data contract: validate degradation events list."""
    _require(isinstance(data_contract, dict), "data_contract must be a mapping")
    
    dvs = data_contract.get("dvs", {})
    _require(isinstance(dvs, dict), "data_contract.dvs must be a mapping")
    
    events = dvs.get("degradation_events", [])
    _require(isinstance(events, list), "data_contract.dvs.degradation_events must be a list")
    
    by_id: Dict[str, Any] = {}
    for idx, ev in enumerate(events):
        _require(isinstance(ev, dict), f"data_contract.dvs.degradation_events[{idx}] must be an object")
        _require("id" in ev, f"data_contract.dvs.degradation_events[{idx}] missing 'id'")
        ev_id = ev["id"].strip()
        _require(ev_id not in by_id, f"duplicate data_contract.dvs.degradation_events id: {ev_id}")
        by_id[ev_id] = ev
    
    dvs["degradation_events_by_id"] = by_id
    data_contract["dvs"] = dvs
    return data_contract


def normalize_strategy_templates(strategy: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize strategy templates: validate template list."""
    _require(isinstance(strategy, dict), "strategy_templates must be a mapping")
    
    templates = strategy.get("strategy_templates", [])
    _require(isinstance(templates, list), "strategy_templates.strategy_templates must be a list")
    
    by_id: Dict[str, Any] = {}
    for idx, tmpl in enumerate(templates):
        _require(isinstance(tmpl, dict), f"strategy_templates[{idx}] must be an object")
        _require("id" in tmpl, f"strategy_templates[{idx}] missing 'id'")
        tmpl_id = tmpl["id"].strip()
        _require(tmpl_id not in by_id, f"duplicate strategy template id: {tmpl_id}")
        by_id[tmpl_id] = tmpl
    
    strategy["strategy_templates_by_id"] = by_id
    return strategy


def normalize_risk_model(risk: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize risk model: validate kill-switch triggers list."""
    _require(isinstance(risk, dict), "risk_model must be a mapping")
    
    kill_switch = risk.get("kill_switch", {})
    if isinstance(kill_switch, dict):
        triggers = kill_switch.get("triggers", [])
        _require(isinstance(triggers, list), "risk_model.kill_switch.triggers must be a list")
        
        by_id: Dict[str, Any] = {}
        for idx, trigger in enumerate(triggers):
            _require(isinstance(trigger, dict), f"kill_switch.triggers[{idx}] must be an object")
            _require("id" in trigger, f"kill_switch.triggers[{idx}] missing 'id'")
            trig_id = trigger["id"].strip()
            _require(trig_id not in by_id, f"duplicate kill_switch trigger id: {trig_id}")
            by_id[trig_id] = trigger
        
        kill_switch["triggers_by_id"] = by_id
        risk["kill_switch"] = kill_switch
    
    return risk


def normalize_calendar(calendar: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize calendar: validate holidays and half_days lists."""
    _require(isinstance(calendar, dict), "calendar must be a mapping")
    
    holidays = calendar.get("holidays", [])
    _require(isinstance(holidays, list), "calendar.holidays must be a list")
    
    half_days = calendar.get("half_days", [])
    _require(isinstance(half_days, list), "calendar.half_days must be a list")
    
    # Build date lookups
    holiday_dates = {h["date"] for h in holidays if isinstance(h, dict) and "date" in h}
    half_day_dates = {h["date"] for h in half_days if isinstance(h, dict) and "date" in h}
    
    calendar["holiday_dates"] = sorted(holiday_dates)
    calendar["half_day_dates"] = sorted(half_day_dates)
    
    return calendar
