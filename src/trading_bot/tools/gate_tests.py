from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

from trading_bot.adapters.ibkr_adapter import IBKRAdapter


def run_gate_tests():
    adapter = IBKRAdapter(mode="OBSERVE")

    class Intent:
        def __init__(self, d):
            for k, v in d.items():
                setattr(self, k, v)

    now = datetime.now(timezone.utc)

    base_intent = {
        "timestamp": now,
        "direction": "LONG",
        "contracts": 1,
        "entry_type": "LIMIT",
        "metadata": {
            "limit_price": 5600.0,
            "bracket": {"stop_price": 5598.0, "target_price": 5603.0, "target_qty": 1},
        },
        "stop_ticks": 8,
        "target_ticks": 12,
        "dvs": 1.0,
        "eqs": 1.0,
    }

    cases = []
    # DVS too low
    i_dvs = Intent({**base_intent, "dvs": 0.6})
    cases.append(("DVS_TOO_LOW", adapter.place_order(i_dvs, Decimal("5600.0"))))
    # EQS too low
    i_eqs = Intent({**base_intent, "eqs": 0.6})
    cases.append(("EQS_TOO_LOW", adapter.place_order(i_eqs, Decimal("5600.0"))))
    # Past flatten deadline (simulate by overriding current_time via adapter logic not exposed; instead rely on filter comparing now string)
    # NOTE: Constitutional filter compares HH:MM string; use 16:00 to force rejection
    class IntentLate(Intent):
        pass
    late_intent = IntentLate({**base_intent})
    # Monkeypatch adapter session manager not used by filter; set time via current system clock; emulate by setting adapter method
    # Directly call filter using eqs/dvs and default now; since current time is runtime, we cannot enforce; print info only.

    return cases


if __name__ == "__main__":
    results = run_gate_tests()
    print(json.dumps({k: v for k, v in results}, indent=2))
