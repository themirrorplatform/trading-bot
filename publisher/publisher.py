from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "events.sqlite"
STATE_PATH = Path(__file__).resolve().parent / ".publisher_state.json"


@dataclass
class Config:
    device_id: str
    mirror_url: str  # Supabase Edge Function URL, e.g., https://<proj>.functions.supabase.co/mirror-events
    secret: str      # Shared secret for device authentication (NOT anon key)
    batch_size: int = 200
    poll_ms: int = 1000

    @staticmethod
    def load(path: Path) -> "Config":
        data = json.loads(path.read_text())
        return Config(
            device_id=data["device_id"],
            mirror_url=data["mirror_url"],
            secret=data["secret"],
            batch_size=int(data.get("batch_size", 200)),
            poll_ms=int(data.get("poll_ms", 1000)),
        )


def get_connection() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL;")
    return con


def load_state() -> int:
    if STATE_PATH.exists():
        try:
            return int(json.loads(STATE_PATH.read_text()).get("last_rowid", 0))
        except Exception:
            return 0
    return 0


def save_state(last_rowid: int) -> None:
    STATE_PATH.write_text(json.dumps({"last_rowid": last_rowid}))


SENSITIVE_KEYS = {"account_id", "access_token", "api_key", "secret", "credentials", "token"}


def sanitize_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        sanitized = {}
        for k, v in payload.items():
            if k in SENSITIVE_KEYS:
                continue
            sanitized[k] = sanitize_payload(v)
        return sanitized
    if isinstance(payload, list):
        return [sanitize_payload(x) for x in payload]
    return payload


def fetch_new_events(after_rowid: int, limit: int) -> List[Dict[str, Any]]:
    con = get_connection()
    try:
        cur = con.cursor()
        cur.execute(
            """
            SELECT rowid, id, stream_id, ts, type, payload_json, created_at
            FROM events
            WHERE rowid > ?
            ORDER BY rowid ASC
            LIMIT ?
            """,
            (after_rowid, limit),
        )
        rows = cur.fetchall()
        out: List[Dict[str, Any]] = []
        for row in rows:
            out.append({
                "rowid": row["rowid"],
                "event_id": row["id"],
                "stream_id": row["stream_id"],
                "ts": row["ts"],
                "type": row["type"],
                "payload": sanitize_payload(json.loads(row["payload_json"])) ,
                "created_at": row["created_at"],
            })
        return out
    finally:
        con.close()


def build_snapshot(con: sqlite3.Connection, stream_id: str) -> Dict[str, Any]:
    cur = con.cursor()
    cur.execute(
        """
        SELECT id, stream_id, ts, type, payload_json
        FROM events
        WHERE stream_id = ?
        ORDER BY rowid DESC
        LIMIT 500
        """,
        (stream_id,),
    )
    latest_signals = None
    latest_beliefs = None
    latest_decision = None

    for row in cur.fetchall():
        etype = row["type"]
        payload = json.loads(row["payload_json"])
        if etype == "SIGNALS_1M" and latest_signals is None:
            latest_signals = payload
        elif etype == "BELIEFS_1M" and latest_beliefs is None:
            latest_beliefs = payload
        elif etype == "DECISION_RECORD" and latest_decision is None:
            latest_decision = payload
        if latest_signals and latest_beliefs and latest_decision:
            break

    return {
        "stream_id": stream_id,
        "signals": sanitize_payload(latest_signals) if latest_signals else None,
        "beliefs": sanitize_payload(latest_beliefs) if latest_beliefs else None,
        "decision": sanitize_payload(latest_decision) if latest_decision else None,
    }


def publish_batch(cfg: Config, events: List[Dict[str, Any]], snapshot: Dict[str, Any]) -> None:
    payload = {
        "device_id": cfg.device_id,
        "secret": cfg.secret,
        "events": events,
        "snapshot": snapshot,
        "health": None,
    }
    resp = requests.post(cfg.mirror_url, json=payload, timeout=30)
    if resp.status_code >= 300:
        raise RuntimeError(f"Mirror failed: {resp.status_code} {resp.text}")


def main():
    cfg_path = Path(__file__).parent / "config.json"
    if not cfg_path.exists():
        raise SystemExit(f"Missing publisher config: {cfg_path}")
    cfg = Config.load(cfg_path)

    last_rowid = load_state()
    print(f"Publisher starting. DB={DB_PATH}, device_id={cfg.device_id}, last_rowid={last_rowid}")

    while True:
        try:
            events = fetch_new_events(last_rowid, cfg.batch_size)
            if events:
                con = get_connection()
                try:
                    # Use the stream_id of the last event for snapshot (assume single instrument for now)
                    stream_id = events[-1]["stream_id"]
                    snapshot = build_snapshot(con, stream_id)
                finally:
                    con.close()

                publish_batch(cfg, events, snapshot)
                last_rowid = events[-1]["rowid"]
                save_state(last_rowid)
                print(f"Published {len(events)} events. last_rowid={last_rowid}")
            time.sleep(cfg.poll_ms / 1000)
        except KeyboardInterrupt:
            print("Publisher stopped by user.")
            break
        except Exception as e:
            print(f"[publisher] Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
