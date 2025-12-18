from __future__ import annotations

from pathlib import Path
from trading_bot.core.types import Event
from trading_bot.log.event_store import EventStore


def test_event_store_idempotent_insert(tmp_path: Path):
    db = tmp_path / "events.db"
    schema = Path(__file__).resolve().parents[1] / "src" / "trading_bot" / "log" / "schema.sql"
    store = EventStore(str(db))
    store.init_schema(str(schema))

    cfg = "cfg_hash_example"
    e = Event.make("STREAM", "2025-12-18T09:31:00-05:00", "BAR_1M", {"c": 100.0}, cfg)

    first = store.append(e)
    second = store.append(e)

    assert first is True
    assert second is False

    events = store.read_stream("STREAM")
    assert len(events) == 1
