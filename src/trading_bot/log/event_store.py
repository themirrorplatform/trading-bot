from __future__ import annotations

import sqlite3
from typing import Iterable, List, Optional
from pathlib import Path
import json

from trading_bot.core.types import Event

class EventStore:
    """Append-only, idempotent event store."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")
        return con

    def init_schema(self, schema_sql_path: str) -> None:
        con = self.connect()
        try:
            with open(schema_sql_path, "r", encoding="utf-8") as f:
                con.executescript(f.read())
            con.commit()
        finally:
            con.close()

    def append(self, e: Event) -> bool:
        """Returns True if inserted, False if already existed."""
        con = self.connect()
        try:
            cur = con.cursor()
            cur.execute(
                """
                INSERT OR IGNORE INTO events (id, stream_id, ts, type, payload_json, config_hash)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (e.event_id, e.stream_id, e.ts, e.type, e.payload_json(), e.config_hash),
            )
            con.commit()
            return cur.rowcount == 1
        finally:
            con.close()

    def append_many(self, events: Iterable[Event]) -> int:
        con = self.connect()
        try:
            cur = con.cursor()
            rows = [(e.event_id, e.stream_id, e.ts, e.type, e.payload_json(), e.config_hash) for e in events]
            cur.executemany(
                """
                INSERT OR IGNORE INTO events (id, stream_id, ts, type, payload_json, config_hash)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            con.commit()
            return cur.rowcount
        finally:
            con.close()

    def read_stream(self, stream_id: str, start_ts: Optional[str] = None, end_ts: Optional[str] = None) -> List[Event]:
        con = self.connect()
        try:
            cur = con.cursor()
            q = "SELECT id, stream_id, ts, type, payload_json, config_hash FROM events WHERE stream_id = ?"
            args = [stream_id]
            if start_ts:
                q += " AND ts >= ?"
                args.append(start_ts)
            if end_ts:
                q += " AND ts <= ?"
                args.append(end_ts)
            q += " ORDER BY ts ASC"
            cur.execute(q, args)
            out: List[Event] = []
            for eid, sid, ts, etype, payload_json, config_hash in cur.fetchall():
                payload = json.loads(payload_json)
                out.append(Event(event_id=eid, stream_id=sid, ts=ts, type=etype, payload=payload, config_hash=config_hash))
            return out
        finally:
            con.close()
