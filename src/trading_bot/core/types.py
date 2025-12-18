from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Literal
import json
import hashlib

EventType = Literal[
    "BAR_1M",
    "SIGNALS_1M",
    "BELIEFS_1M",
    "DECISION_1M",
    "DECISION_RECORD",
    "ATTRIBUTION",
    "RECONCILIATION",
    "ORDER_INTENT",
    "ORDER_EVENT",
    "FILL_EVENT",
    "POSITION_SNAPSHOT",
    "OVERRIDE_EVENT",
    "SYSTEM_EVENT",
    "ROLLOVER_EVENT",
]

def stable_json(obj: Any) -> str:
    # Deterministic JSON serialization
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class Event:
    event_id: str
    stream_id: str
    ts: str            # ISO8601 timestamp string (must be consistent timezone policy)
    type: EventType
    payload: Dict[str, Any]
    config_hash: str

    @staticmethod
    def make(stream_id: str, ts: str, type: EventType, payload: Dict[str, Any], config_hash: str) -> "Event":
        base = {
            "stream_id": stream_id,
            "ts": ts,
            "type": type,
            "payload": payload,
            "config_hash": config_hash,
        }
        eid = sha256_hex(stable_json(base))
        return Event(event_id=eid, **base)

    def payload_json(self) -> str:
        return stable_json(self.payload)

@dataclass(frozen=True)
class Bar1m:
    symbol: str
    ts: str
    o: float
    h: float
    l: float
    c: float
    v: float

    def to_payload(self) -> Dict[str, Any]:
        return asdict(self)
