from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from trading_bot.core.types import Event, stable_json
from trading_bot.log.event_store import EventStore


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DecisionRecord:
    """
    Human-readable + machine-parseable decision record.

    This is emitted on every decision cycle: either a trade intent or a skip with reasons.
    """
    time: str
    instrument: str
    action: str  # ENTER | HOLD | EXIT | MODIFY | SKIP
    setup_scores: Dict[str, float]  # e.g., {"F1": 0.72, "F3": 0.41}
    euc_score: Optional[float]
    reasons: Dict[str, Any]  # structured reason codes and values
    plain_english: str       # concise summary for a human
    context: Dict[str, Any]  # dvs, eqs, session_phase, friction, etc.


class DecisionJournal:
    """
    Append DecisionRecord events to the EventStore with type DECISION_RECORD.
    """

    def __init__(self, store: EventStore, stream_id: str, config_hash: str):
        self.store = store
        self.stream_id = stream_id
        self.config_hash = config_hash

    def log(self, record: DecisionRecord) -> bool:
        payload = asdict(record)
        e = Event.make(
            stream_id=self.stream_id,
            ts=record.time,
            type="DECISION_RECORD",
            payload=payload,
            config_hash=self.config_hash,
        )
        return self.store.append(e)

    @staticmethod
    def summarize_no_trade(setup_scores: Dict[str, float], reasons: Dict[str, Any], context: Dict[str, Any]) -> str:
        # Build a compact plain-English summary
        bits = []
        if 'reason_code' in reasons:
            bits.append(f"Skipped: {reasons['reason_code']}")
        if 'details' in reasons:
            details = reasons['details']
            if isinstance(details, dict):
                for k, v in details.items():
                    bits.append(f"{k}={v}")
        if context:
            for k in ('dvs','eqs','session_phase','friction_usd','spread_ticks'):
                if k in context:
                    bits.append(f"{k}={context[k]}")
        if setup_scores:
            top = sorted(setup_scores.items(), key=lambda kv: kv[1], reverse=True)[:3]
            if top:
                tops = ", ".join([f"{k}:{v:.2f}" for k, v in top])
                bits.append(f"setups=({tops})")
        return "; ".join(bits) or "Skipped: unspecified"

    @staticmethod
    def summarize_trade(action: str, setup_id: str, euc_score: Optional[float], context: Dict[str, Any]) -> str:
        parts = [f"{action}: {setup_id}"]
        if euc_score is not None:
            parts.append(f"EUC={euc_score:.2f}")
        for k in ('dvs','eqs','session_phase','friction_usd'):
            if k in context:
                parts.append(f"{k}={context[k]}")
        return "; ".join(parts)
