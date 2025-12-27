from __future__ import annotations

import json
from decimal import Decimal
from datetime import datetime

from trading_bot.core.runner import BotRunner

# Synthetic bars: chop → trend → chop
REGIME_BARS = [
    # Chop: 10 bars, small ranges
    *[{"ts": f"2025-12-24T10:{i:02d}:00-05:00", "o": 5600.0 + (i % 3 - 1) * 0.5, "h": 5600.5 + (i % 3 - 1) * 0.5, "l": 5599.5 + (i % 3 - 1) * 0.5, "c": 5600.0 + (i % 3 - 1) * 0.5, "v": 1000, "bid": 5599.75, "ask": 5600.25} for i in range(10)],
    # Trend: 10 bars, strong directional move
    *[{"ts": f"2025-12-24T10:{10+i:02d}:00-05:00", "o": 5600.0 + i * 2.0, "h": 5602.0 + i * 2.0, "l": 5599.0 + i * 2.0, "c": 5601.0 + i * 2.0, "v": 2000, "bid": 5600.75 + i * 2.0, "ask": 5601.25 + i * 2.0} for i in range(10)],
    # Chop again: 10 bars
    *[{"ts": f"2025-12-24T10:{20+i:02d}:00-05:00", "o": 5620.0 + (i % 3 - 1) * 0.5, "h": 5620.5 + (i % 3 - 1) * 0.5, "l": 5619.5 + (i % 3 - 1) * 0.5, "c": 5620.0 + (i % 3 - 1) * 0.5, "v": 1000, "bid": 5619.75, "ask": 5620.25} for i in range(10)],
]


def run_regime_switch():
    runner = BotRunner(db_path="data/events.sqlite", adapter="ibkr", fill_mode="IMMEDIATE")
    decisions = []
    for bar in REGIME_BARS:
        d = runner.run_once(bar, stream_id="REGIME_TEST")
        decisions.append({
            "ts": bar["ts"],
            "action": d.get("action"),
            "reason": d.get("reason"),
            "beliefs": d.get("metadata", {}).get("beliefs", {}),
        })
    return decisions


if __name__ == "__main__":
    results = run_regime_switch()
    print(json.dumps(results, indent=2))
