from __future__ import annotations

from collections import Counter
from typing import List, Dict, Any
from trading_bot.core.types import Event

def summarize_no_trade_reasons(events: List[Event]) -> Dict[str, Any]:
    reasons = Counter()
    for e in events:
        if e.type == "DECISION_1M":
            r = e.payload.get("no_trade_reason")
            if r:
                reasons[r] += 1
    return {
        "no_trade_reasons": dict(reasons),
        "total_decisions": sum(reasons.values()),
    }
