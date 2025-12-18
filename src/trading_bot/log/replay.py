from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Any, List, Optional

from trading_bot.core.types import Event

@dataclass
class ReplayResult:
    stream_id: str
    config_hash: str
    events_in: int
    events_out: int
    output_fingerprint: str
    notes: Dict[str, Any]

def replay_events(
    events: List[Event],
    handler: Callable[[Event], Optional[Event]],
    fingerprint_fn: Callable[[List[Event]], str],
) -> ReplayResult:
    out: List[Event] = []
    stream_id = events[0].stream_id if events else "EMPTY"
    config_hash = events[0].config_hash if events else "EMPTY"

    for e in events:
        generated = handler(e)
        if generated is not None:
            out.append(generated)

    fp = fingerprint_fn(out)
    return ReplayResult(
        stream_id=stream_id,
        config_hash=config_hash,
        events_in=len(events),
        events_out=len(out),
        output_fingerprint=fp,
        notes={},
    )
