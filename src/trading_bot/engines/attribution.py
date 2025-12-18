"""Component 6: Attribution Engine (stub).

Mechanical ordered-first-match classification A0-A9 using configured lookforward windows.
Outputs an attribution record and process/outcome scores.
"""
from __future__ import annotations

from typing import Dict, Any


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _matches_condition(cond: Any, metrics: Dict[str, Any]) -> bool:
    if cond is None:
        return False
    if isinstance(cond, dict):
        for key, val in cond.items():
            if key.endswith("_gte"):
                metric = key[:-4]
                if metrics.get(metric) is None or float(metrics[metric]) < float(val):
                    return False
            elif key.endswith("_gt"):
                metric = key[:-3]
                if metrics.get(metric) is None or float(metrics[metric]) <= float(val):
                    return False
            elif key.endswith("_lte"):
                metric = key[:-4]
                if metrics.get(metric) is None or float(metrics[metric]) > float(val):
                    return False
            elif key.endswith("_lt"):
                metric = key[:-3]
                if metrics.get(metric) is None or float(metrics[metric]) >= float(val):
                    return False
            elif key.endswith("_eq"):
                metric = key[:-3]
                if metrics.get(metric) != val:
                    return False
            else:
                return False
        return True
    return False


def attribute(trade_record: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ordered-first-match attribution A0–A9 with simple rule conditions.

    cfg typical shape:
    {
      "rules": [
        {"id": "A1_FAST_REVERSION", "condition": {"duration_seconds_lte": 120, "pnl_usd_gt": 0}, "process_score": 0.8, "outcome_score": 0.9},
        {"id": "A2_SLOW_REVERSION", "condition": {"duration_seconds_gt": 120, "pnl_usd_gt": 0}}
      ],
      "default": {"id": "A0_UNCLASSIFIED", "process_score": 0.5, "outcome_score": 0.5}
    }
    """

    rules = cfg.get("rules", []) or []
    default_rule = cfg.get("default", {"id": "A0_UNCLASSIFIED", "process_score": 0.5, "outcome_score": 0.5})

    # Build metrics from trade record
    entry_price = trade_record.get("entry_price")
    exit_price = trade_record.get("exit_price")
    pnl_usd = trade_record.get("pnl_usd")
    duration_seconds = trade_record.get("duration_seconds")
    slippage_ticks = trade_record.get("slippage_ticks")
    spread_ticks = trade_record.get("spread_ticks")
    eqs = trade_record.get("eqs")
    dvs = trade_record.get("dvs")

    metrics = {
        "entry_price": entry_price,
        "exit_price": exit_price,
        "pnl_usd": pnl_usd,
        "duration_seconds": duration_seconds,
        "slippage_ticks": slippage_ticks,
        "spread_ticks": spread_ticks,
        "eqs": eqs,
        "dvs": dvs,
    }

    chosen = None
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        if _matches_condition(rule.get("condition"), metrics):
            chosen = rule
            break

    if chosen is None:
        chosen = default_rule

    proc = float(chosen.get("process_score", 0.5) or 0.5)
    outc = float(chosen.get("outcome_score", 0.5) or 0.5)

    return {
        "classification": chosen.get("id", "A0_UNCLASSIFIED"),
        "process_score": _clamp01(proc),
        "outcome_score": _clamp01(outc),
        "metrics": metrics,
    }
