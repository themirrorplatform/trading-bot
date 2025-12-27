from __future__ import annotations

import json
from decimal import Decimal

from trading_bot.core.runner import BotRunner

# Friction torture: simulate high slippage and spread via bar metadata
BAR_LOW_FRICTION = {
    "ts": "2025-12-24T10:01:00-05:00",
    "o": 5600.0,
    "h": 5601.5,
    "l": 5598.5,
    "c": 5600.5,
    "v": 1200,
    "expected_slippage": 0.25,  # 1 tick
    "spread_ticks": 1,
}

BAR_HIGH_FRICTION = {
    "ts": "2025-12-24T10:02:00-05:00",
    "o": 5600.0,
    "h": 5601.5,
    "l": 5598.5,
    "c": 5600.5,
    "v": 1200,
    "expected_slippage": 3.0,  # 12 ticks
    "spread_ticks": 5,
}


def run_friction_torture():
    runner_low = BotRunner(db_path="data/events.sqlite", adapter="ibkr", fill_mode="IMMEDIATE")
    runner_high = BotRunner(db_path="data/events.sqlite", adapter="ibkr", fill_mode="IMMEDIATE")
    d_low = runner_low.run_once(BAR_LOW_FRICTION, stream_id="FRICTION_LOW")
    d_high = runner_high.run_once(BAR_HIGH_FRICTION, stream_id="FRICTION_HIGH")
    return {"low_friction": d_low, "high_friction": d_high}


if __name__ == "__main__":
    results = run_friction_torture()
    print(json.dumps(results, indent=2))
