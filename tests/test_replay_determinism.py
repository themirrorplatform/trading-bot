from __future__ import annotations

from trading_bot.core.types import Event, sha256_hex, stable_json
from trading_bot.log.replay import replay_events


def fingerprint(events):
    return sha256_hex(stable_json([
        {"ts": e.ts, "type": e.type, "payload": e.payload}
        for e in events
    ]))


def handler(e: Event):
    # placeholder: echo deterministic decision for each bar
    if e.type == "BAR_1M":
        payload = {"decision": "NO_TRADE", "no_trade_reason": "PLACEHOLDER"}
        return Event.make(stream_id=e.stream_id, ts=e.ts, type="DECISION_1M", payload=payload, config_hash=e.config_hash)
    return None


def test_determinism():
    cfg = "cfg_hash_example"
    stream = "MES_RTH_2025-12-18"
    bars = [
        Event.make(stream, "2025-12-18T09:31:00-05:00", "BAR_1M", {"c": 100.0}, cfg),
        Event.make(stream, "2025-12-18T09:32:00-05:00", "BAR_1M", {"c": 101.0}, cfg),
    ]
    r1 = replay_events(bars, handler, fingerprint)
    r2 = replay_events(bars, handler, fingerprint)
    assert r1.output_fingerprint == r2.output_fingerprint
