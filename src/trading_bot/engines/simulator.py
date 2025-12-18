"""Component 5: Simulated Execution (stub).

Applies pessimistic friction model and simulates fills to validate expectancy after costs.
Outputs FILL_EVENT payloads.
"""
from __future__ import annotations

from typing import Dict, Any


def simulate_fills(order_intent_payload: Dict[str, Any], market_payload: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Minimal simulated fill with pessimistic friction model.

    Inputs:
    - order_intent_payload: includes direction (LONG/SHORT) and contracts
    - market_payload: includes last_price and spread_ticks
    - cfg: may include tick_size, slippage_ticks, spread_to_slippage_ratio

    Returns a FILL_EVENT-like dict with fill_price and slippage_ticks.
    """

    direction = str(order_intent_payload.get("direction", "LONG")).upper()
    contracts = int(order_intent_payload.get("contracts", 1) or 1)
    last_price = market_payload.get("last_price")
    spread_ticks = int(market_payload.get("spread_ticks", 0) or 0)

    try:
        price = float(last_price)
    except (TypeError, ValueError):
        price = 0.0

    tick_size = float(cfg.get("tick_size", 0.25) or 0.25)
    base_slip_ticks = int(cfg.get("slippage_ticks", 1) or 1)
    spread_to_slip = float(cfg.get("spread_to_slippage_ratio", 0.5) or 0.5)

    slippage_ticks = max(0, int(round(base_slip_ticks + spread_to_slip * spread_ticks)))
    slip_price = slippage_ticks * tick_size

    if direction == "LONG":
        fill_price = price + slip_price
    else:
        fill_price = price - slip_price

    return {
        "type": "FILL_EVENT",
        "payload": {
            "direction": direction,
            "contracts": contracts,
            "requested_price": price,
            "fill_price": fill_price,
            "slippage_ticks": slippage_ticks,
            "spread_ticks": spread_ticks,
        },
    }
