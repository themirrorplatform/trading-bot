"""Data Validity Score (DVS) and Execution Quality Score (EQS) computation.

EQS:
- Consumes structured execution_contract.yaml
- `eqs.degradation_events` is a LIST of rule objects (id, condition, penalties)
- Deterministic ordered evaluation; penalties applied once per step; clamped to [0,1]

DVS:
- Consumes structured data_contract.yaml
- `dvs.degradation_events` is a LIST of rule objects (id, condition, penalties)
- Deterministic ordered evaluation; penalties applied once per step; clamped to [0,1]

Conditions use a small explicit parser with suffix operators (`_gte`, `_lte`,
`_gt`, `_lt`, `_eq`). Unknown shapes fail closed (do not match).
"""

from __future__ import annotations

from typing import Any, Dict, List


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _matches_condition(cond: Any, metrics: Dict[str, Any]) -> bool:
    """Evaluate a structured condition safely; unknown shapes fail-closed (False)."""
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

    # Fail-closed for any non-dict conditions
    return False


def _apply_penalty(eqs: float, ev: Dict[str, Any]) -> float:
    """Apply immediate penalty from event; support both immediate_penalty and penalties.eqs_delta."""
    if not isinstance(ev, dict):
        return eqs

    if "immediate_penalty" in ev:
        delta = float(ev.get("immediate_penalty", 0.0))
        return clamp01(eqs - delta)

    penalties = ev.get("penalties", {})
    if isinstance(penalties, dict):
        delta = float(penalties.get("eqs_delta", 0.0))
        return clamp01(eqs + delta)

    return eqs


def _apply_recovery(eqs: float, recovery_cfg: Any) -> float:
    """Simple linear recovery per step if configured."""
    if not isinstance(recovery_cfg, dict):
        return eqs
    per_bar = float(recovery_cfg.get("eqs_recovery_per_bar", 0.0))
    return clamp01(eqs + per_bar)


def compute_eqs(state: Dict[str, Any], execution_contract: Dict[str, Any]) -> float:
    """
    Compute EQS given current execution state and the normalized execution contract.

    - Uses eqs.degradation_events LIST in order
    - Applies each triggered event once per evaluation step
    - Clamps to [0,1]
    - Recovery is optional and linear if configured
    """

    eqs_cfg = (execution_contract or {}).get("eqs", {})
    events: List[Dict[str, Any]] = eqs_cfg.get("degradation_events", []) or []

    # Start from state-provided EQS or contract initial_value
    eqs_val = state.get("eqs")
    if eqs_val is None:
        eqs_val = eqs_cfg.get("initial_value", 1.0)
    eqs_val = float(eqs_val)

    # Metrics snapshot; state keys should be set by the caller
    # Normalize metrics for structured conditions
    fill_price = state.get("fill_price")
    limit_price = state.get("limit_price")
    expected_slippage = state.get("expected_slippage")
    slippage_vs_expected = None
    # Get EPS floor from contract, fallback to 1e-9
    EPS = eqs_cfg.get("slippage_min_expected", 1e-9)
    if fill_price is not None and limit_price is not None and expected_slippage is not None:
        try:
            denom = max(float(expected_slippage), EPS)
            slippage_vs_expected = abs(float(fill_price) - float(limit_price)) / denom
        except Exception:
            slippage_vs_expected = None

    metrics = {
        "order_rejected": bool(state.get("order_rejected")),
        "fill_time_minus_order_time_seconds": state.get("fill_time_minus_order_time_seconds"),
        "partial_fill": bool(state.get("partial_fill")),
        "order_state": str(state.get("order_state", "")).upper() if state.get("order_state") is not None else None,
        "connection_state": str(state.get("connection_state", "")).upper() if state.get("connection_state") is not None else None,
        "slippage_ticks": state.get("slippage_ticks"),
        "slippage_vs_expected": slippage_vs_expected,
    }

    # Deterministic evaluation: list order is authoritative
    for ev in events:
        if not isinstance(ev, dict):
            continue
        if _matches_condition(ev.get("condition"), metrics):
            eqs_val = _apply_penalty(eqs_val, ev)

    eqs_val = _apply_recovery(eqs_val, eqs_cfg.get("recovery"))
    return clamp01(eqs_val)


def _apply_dvs_penalty(dvs: float, ev: Dict[str, Any]) -> float:
    """Apply immediate penalty from DVS event; supports immediate_penalty or penalties.dvs_delta."""
    if not isinstance(ev, dict):
        return dvs
    if "immediate_penalty" in ev:
        delta = float(ev.get("immediate_penalty", 0.0))
        return clamp01(dvs - delta)
    penalties = ev.get("penalties", {})
    if isinstance(penalties, dict):
        delta = float(penalties.get("dvs_delta", 0.0))
        # Note: delta is expected negative for degradation; still clamp
        return clamp01(dvs + delta)
    return dvs


def _apply_dvs_recovery(dvs: float, recovery_cfg: Any) -> float:
    """Simple linear DVS recovery per step if configured."""
    if not isinstance(recovery_cfg, dict):
        return dvs
    per_bar = float(recovery_cfg.get("dvs_recovery_per_bar", 0.0))
    return clamp01(dvs + per_bar)


def compute_dvs(state: Dict[str, Any], data_contract: Dict[str, Any]) -> float:
    """
    Compute DVS given current data validity state and the normalized data contract.

    - Uses dvs.degradation_events LIST in order
    - Applies each triggered event once per evaluation step
    - Clamps to [0,1]
    - Optional linear recovery if configured
    """

    dvs_cfg = (data_contract or {}).get("dvs", {})
    events: List[Dict[str, Any]] = dvs_cfg.get("degradation_events", []) or []

    # Start from state-provided DVS or contract initial_value
    dvs_val = state.get("dvs")
    if dvs_val is None:
        dvs_val = dvs_cfg.get("initial_value", 1.0)
    dvs_val = float(dvs_val)

    # Metrics snapshot; callers should populate these keys as appropriate
    metrics = {
        # Common data quality metrics
        "bar_lag_seconds": state.get("bar_lag_seconds"),
        "missing_fields": int(state.get("missing_fields", 0) or 0),
        "gap_detected": bool(state.get("gap_detected")),
        "outlier_score": state.get("outlier_score"),
        "symbol_changed": bool(state.get("symbol_changed")),
        "session_anomaly": bool(state.get("session_anomaly")),
        "trading_halt": bool(state.get("trading_halt")),
        # Price/volume plausibility
        "price_jump_pct": state.get("price_jump_pct"),
        "volume_spike_ratio": state.get("volume_spike_ratio"),
    }

    # Deterministic evaluation: list order is authoritative
    for ev in events:
        if not isinstance(ev, dict):
            continue
        if _matches_condition(ev.get("condition"), metrics):
            dvs_val = _apply_dvs_penalty(dvs_val, ev)

    dvs_val = _apply_dvs_recovery(dvs_val, dvs_cfg.get("recovery"))
    return clamp01(dvs_val)
