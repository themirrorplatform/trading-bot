from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class PostTradeScores:
    edge_score: float
    luck_score: float
    execution_score: float
    learning_weight: float
    classification: str
    notes: str


def compute_edge_score(forecast: Dict[str, Any]) -> float:
    """
    Edge proxy at entry from forecast snapshot.
    Expects keys:
      - expected_return_ticks
      - belief_probability (0-1)
      - friction_usd
      - tick_value (default 1.25 if missing)
    """
    er_ticks = float(forecast.get("expected_return_ticks", 0) or 0)
    p = float(forecast.get("belief_probability", 0.5) or 0.5)
    tick_value = float(forecast.get("tick_value", 1.25) or 1.25)
    friction = float(forecast.get("friction_usd", 9.0) or 9.0)
    # Lower-bound probability haircut
    p_lb = max(0.0, min(1.0, p * 0.8))
    er_usd = er_ticks * tick_value * p_lb
    if er_usd <= 0:
        return 0.0
    # Normalize against $12 expected move for scale ~1.0
    return _clamp01(er_usd / 12.0)


def compute_luck_score(path: Dict[str, Any], plan: Dict[str, Any]) -> float:
    """
    Luck ~ surprise between realized path and plan.
    Expects:
      path: { mae_ticks, mfe_ticks, time_to_target_s, time_to_stop_s, hit: "target|stop|exit" }
      plan: { stop_ticks, target_ticks, expected_time_to_target_s }
    Heuristics:
      - Near-stop then win => high luck
      - Quick clean win near expected time => low luck
      - Slow grind win with large MAE => medium-high luck
    """
    mae = float(path.get("mae_ticks", 0) or 0)
    mfe = float(path.get("mfe_ticks", 0) or 0)
    hit = path.get("hit")  # "target" | "stop" | "exit"
    t_hit = float(path.get("time_to_hit_s", 0) or 0)
    stop_ticks = float(plan.get("stop_ticks", 8) or 8)
    expected_t = float(plan.get("expected_time_to_target_s", 900) or 900)

    near_stop = 1.0 if stop_ticks > 0 and mae >= 0.8 * stop_ticks else 0.0
    quick = 1.0 if 0 < t_hit <= max(60.0, 0.5 * expected_t) else 0.0
    clean = 1.0 if near_stop == 0.0 and mae <= 0.3 * stop_ticks else 0.0

    if hit == "target":
        # Clean & timely => low luck; near-stop => high luck
        base = 0.2
        luck = base + 0.6 * near_stop - 0.2 * (clean + quick)
    elif hit == "stop":
        # Stopout could be unlucky if early and small MAE (whipsaw)
        base = 0.5
        luck = base - 0.3 * near_stop  # if not near stop, more model error than luck
    else:
        # Managed exit
        base = 0.4
        luck = base + 0.3 * near_stop

    return _clamp01(luck)


def compute_execution_score(exe: Dict[str, Any]) -> float:
    """
    Higher is better. Penalize slippage and partials.
    Expects: { slippage_ticks, spread_ticks, partial_fill, rejects }
    """
    slip = float(exe.get("slippage_ticks", 0) or 0)
    spread = float(exe.get("spread_ticks", 1) or 1)
    partial = 1.0 if exe.get("partial_fill") else 0.0
    rejects = int(exe.get("rejects", 0) or 0)

    # Normalize slippage vs 2 ticks
    slip_penalty = min(1.0, slip / 2.0)
    spread_quality = 1.0 - min(1.0, max(0.0, (spread - 1.0) / 4.0))
    reject_penalty = min(1.0, rejects * 0.3)
    partial_penalty = 0.2 * partial

    score = 1.0 - (0.5 * slip_penalty + 0.2 * (1.0 - spread_quality) + 0.2 * reject_penalty + 0.1 * partial_penalty)
    return _clamp01(score)


def classify_post_trade(pnl_usd: float, luck: float, edge: float, exe_score: float) -> str:
    """Simple A0-A9 style buckets based on scores."""
    if pnl_usd > 0:
        if luck > 0.7 and edge < 0.4:
            return "A0_LUCKY_WIN"
        if exe_score < 0.5:
            return "A8_EXECUTION_HELPED_WIN"
        return "A0_SUCCESS"
    else:
        if luck < 0.3 and edge > 0.6:
            return "A2_UNLUCKY_LOSS"
        if edge < 0.3:
            return "A1_BAD_MODEL"
        if exe_score < 0.5:
            return "A8_EXECUTION_FAILURE"
        return "A9_UNDETERMINED"


def score_post_trade(trade: Dict[str, Any]) -> PostTradeScores:
    """
    Compute Edge, Luck, Execution and LearningWeight for a completed trade.

    Expects trade to contain:
      forecast: { expected_return_ticks, belief_probability, friction_usd, tick_value }
      plan: { stop_ticks, target_ticks, expected_time_to_target_s }
      path: { mae_ticks, mfe_ticks, time_to_hit_s, hit }
      execution: { slippage_ticks, spread_ticks, partial_fill, rejects }
      pnl_usd
    """
    forecast = trade.get("forecast", {})
    plan = trade.get("plan", {})
    path = trade.get("path", {})
    execution = trade.get("execution", {})

    edge = compute_edge_score(forecast)
    luck = compute_luck_score(path, plan)
    exe = compute_execution_score(execution)
    learn_w = _clamp01((1.0 - luck) * exe)

    pnl_usd = float(trade.get("pnl_usd", 0) or 0)
    cls = classify_post_trade(pnl_usd, luck, edge, exe)

    notes = f"edge={edge:.2f}, luck={luck:.2f}, execution={exe:.2f}, learn_w={learn_w:.2f}"
    return PostTradeScores(edge_score=edge, luck_score=luck, execution_score=exe, learning_weight=learn_w, classification=cls, notes=notes)
