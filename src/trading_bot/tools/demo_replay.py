from __future__ import annotations

from trading_bot.core.types import Event, sha256_hex, stable_json
from trading_bot.log.replay import replay_events

def fingerprint(events):
    return sha256_hex(stable_json([{"ts": e.ts, "type": e.type, "payload": e.payload} for e in events]))

def handler(e: Event):
    if e.type == "BAR_1M":
        return Event.make(e.stream_id, e.ts, "DECISION_1M", {"decision":"NO_TRADE","no_trade_reason":"PLACEHOLDER"}, e.config_hash)
    return None

def main():
    cfg = "cfg_hash_example"
    stream = "MES_RTH_DEMO"
    events = [
        Event.make(stream, "2025-12-18T09:31:00-05:00", "BAR_1M", {"o":100,"h":101,"l":99.5,"c":100.5,"v":1200}, cfg),
        Event.make(stream, "2025-12-18T09:32:00-05:00", "BAR_1M", {"o":100.5,"h":100.75,"l":100.0,"c":100.1,"v":900}, cfg),
    ]
    r = replay_events(events, handler, fingerprint)
    print(r)

if __name__ == "__main__":
    main()
