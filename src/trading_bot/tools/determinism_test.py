from __future__ import annotations

import json
from decimal import Decimal

from trading_bot.core.runner import BotRunner

BAR = {"ts": "2025-12-24T10:01:00-05:00", "o": 5600.0, "h": 5601.5, "l": 5598.5, "c": 5600.5, "v": 1200}


def determinism_once():
    r1 = BotRunner(db_path="data/events.sqlite", adapter="ibkr", fill_mode="IMMEDIATE")
    r2 = BotRunner(db_path="data/events.sqlite", adapter="ibkr", fill_mode="IMMEDIATE")
    d1 = r1.run_once(BAR, stream_id="TEST")
    d2 = r2.run_once(BAR, stream_id="TEST")
    return d1, d2


if __name__ == "__main__":
    d1, d2 = determinism_once()
    print(json.dumps({"equal": d1 == d2, "first": d1, "second": d2}, indent=2))
