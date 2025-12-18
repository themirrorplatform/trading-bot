"""
FastAPI backend for trading bot event streaming + snapshot retrieval.
Provides REST + WebSocket endpoints for local debugging and UI.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

DB_PATH = Path(__file__).parent.parent / "data" / "events.sqlite"
POLL_INTERVAL_MS = 200  # Poll SQLite every 200ms for new events


# ─────────────────────────────────────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EventRecord:
    """Canonical event structure for API responses."""
    event_id: str
    stream_id: str
    ts: str
    type: str
    payload: Dict[str, Any]
    config_hash: str
    created_at: str


@dataclass
class ConnectionManager:
    """Manage WebSocket connections and broadcast new events."""
    active_connections: Set[WebSocket]
    last_broadcast_rowid: int = 0

    def __init__(self):
        self.active_connections = set()
        self.last_broadcast_rowid = 0

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        dead_connections = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.add(connection)
        # Clean up dead connections
        self.active_connections -= dead_connections


manager = ConnectionManager()


# ─────────────────────────────────────────────────────────────────────────────
# Database utilities
# ─────────────────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Get SQLite connection with WAL mode."""
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL;")
    return con


def row_to_event(row: sqlite3.Row) -> EventRecord:
    """Convert SQLite row to EventRecord."""
    return EventRecord(
        event_id=row["id"],
        stream_id=row["stream_id"],
        ts=row["ts"],
        type=row["type"],
        payload=json.loads(row["payload_json"]),
        config_hash=row["config_hash"],
        created_at=row["created_at"],
    )


def event_to_dict(event: EventRecord) -> Dict[str, Any]:
    """Convert EventRecord to JSON-serializable dict."""
    return {
        "event_id": event.event_id,
        "stream_id": event.stream_id,
        "ts": event.ts,
        "type": event.type,
        "payload": event.payload,
        "config_hash": event.config_hash,
        "created_at": event.created_at,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Background tasks
# ─────────────────────────────────────────────────────────────────────────────

async def poll_and_broadcast():
    """Poll SQLite for new events and broadcast to WebSocket clients."""
    while True:
        try:
            if manager.active_connections:
                con = get_connection()
                try:
                    # Get new events since last broadcast
                    cur = con.cursor()
                    cur.execute(
                        """
                        SELECT rowid, id, stream_id, ts, type, payload_json, config_hash, created_at
                        FROM events
                        WHERE rowid > ?
                        ORDER BY rowid ASC
                        LIMIT 100
                        """,
                        (manager.last_broadcast_rowid,),
                    )
                    rows = cur.fetchall()

                    if rows:
                        for row in rows:
                            event = row_to_event(row)
                            await manager.broadcast({
                                "type": "EVENT",
                                "event": event_to_dict(event),
                            })
                            manager.last_broadcast_rowid = row["rowid"]

                finally:
                    con.close()

        except Exception as e:
            print(f"[poll_and_broadcast] Error: {e}")

        await asyncio.sleep(POLL_INTERVAL_MS / 1000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background polling task on startup."""
    task = asyncio.create_task(poll_and_broadcast())
    yield
    task.cancel()


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Trading Bot API", version="1.0.0", lifespan=lifespan)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# REST endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    """Get bot status and health check."""
    con = get_connection()
    try:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) as count, MAX(rowid) as max_rowid FROM events")
        row = cur.fetchone()
        total_events = row["count"]
        max_rowid = row["max_rowid"] or 0

        # Get latest event
        cur.execute(
            """
            SELECT id, stream_id, ts, type
            FROM events
            ORDER BY rowid DESC
            LIMIT 1
            """
        )
        latest = cur.fetchone()

        return {
            "status": "ok",
            "total_events": total_events,
            "max_rowid": max_rowid,
            "latest_event": {
                "event_id": latest["id"],
                "stream_id": latest["stream_id"],
                "ts": latest["ts"],
                "type": latest["type"],
            } if latest else None,
            "db_path": str(DB_PATH),
            "timestamp": datetime.utcnow().isoformat(),
        }
    finally:
        con.close()


@app.get("/api/events")
async def get_events(
    stream_id: Optional[str] = None,
    type: Optional[str] = None,
    after_ts: Optional[str] = None,
    before_ts: Optional[str] = None,
    after_rowid: Optional[int] = None,
    limit: int = Query(default=100, le=1000),
):
    """Query events with filters."""
    con = get_connection()
    try:
        query = """
            SELECT rowid, id, stream_id, ts, type, payload_json, config_hash, created_at
            FROM events
            WHERE 1=1
        """
        params = []

        if stream_id:
            query += " AND stream_id = ?"
            params.append(stream_id)

        if type:
            query += " AND type = ?"
            params.append(type)

        if after_ts:
            query += " AND ts >= ?"
            params.append(after_ts)

        if before_ts:
            query += " AND ts <= ?"
            params.append(before_ts)

        if after_rowid is not None:
            query += " AND rowid > ?"
            params.append(after_rowid)

        query += " ORDER BY rowid ASC LIMIT ?"
        params.append(limit)

        cur = con.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()

        events = [event_to_dict(row_to_event(row)) for row in rows]

        return {
            "events": events,
            "count": len(events),
        }
    finally:
        con.close()


@app.get("/api/events/{event_id}")
async def get_event_by_id(event_id: str):
    """Get single event by ID for drawer expansion."""
    con = get_connection()
    try:
        cur = con.cursor()
        cur.execute(
            """
            SELECT rowid, id, stream_id, ts, type, payload_json, config_hash, created_at
            FROM events
            WHERE id = ?
            LIMIT 1
            """,
            (event_id,),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

        event = row_to_event(row)
        return event_to_dict(event)
    finally:
        con.close()


@app.get("/api/snapshot")
async def get_snapshot(
    stream_id: str = Query(default="MES"),
    event_id: Optional[str] = None,
    ts: Optional[str] = None,
):
    """
    Get reconstructed state snapshot at a specific event_id or timestamp.
    Returns the latest signals, beliefs, and decision at that point.
    """
    con = get_connection()
    try:
        query_base = """
            SELECT id, stream_id, ts, type, payload_json, config_hash
            FROM events
            WHERE stream_id = ?
        """
        params = [stream_id]

        if event_id:
            query_base += " AND rowid <= (SELECT rowid FROM events WHERE id = ? LIMIT 1)"
            params.append(event_id)
        elif ts:
            query_base += " AND ts <= ?"
            params.append(ts)

        query_base += " ORDER BY rowid DESC"

        cur = con.cursor()
        cur.execute(query_base, params)
        rows = cur.fetchall()

        # Find latest of each type
        latest_signals = None
        latest_beliefs = None
        latest_decision = None

        for row in rows:
            event = row_to_event(row)
            if event.type == "SIGNALS_1M" and not latest_signals:
                latest_signals = event.payload
            elif event.type == "BELIEFS_1M" and not latest_beliefs:
                latest_beliefs = event.payload
            elif event.type == "DECISION_RECORD" and not latest_decision:
                latest_decision = event.payload

            # Stop once we have all three
            if latest_signals and latest_beliefs and latest_decision:
                break

        return {
            "stream_id": stream_id,
            "snapshot_at": event_id or ts,
            "signals": latest_signals,
            "beliefs": latest_beliefs,
            "decision": latest_decision,
        }
    finally:
        con.close()


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """
    WebSocket endpoint for live event streaming.
    Client sends: {"type": "HELLO", "last_rowid": 12345}
    Server responds with backfill + live stream.
    """
    await manager.connect(websocket)

    try:
        # Wait for HELLO message
        hello = await websocket.receive_json()

        if hello.get("type") == "HELLO":
            last_rowid = hello.get("last_rowid", 0)

            # Backfill events since last_rowid
            con = get_connection()
            try:
                cur = con.cursor()
                cur.execute(
                    """
                    SELECT rowid, id, stream_id, ts, type, payload_json, config_hash, created_at
                    FROM events
                    WHERE rowid > ?
                    ORDER BY rowid ASC
                    LIMIT 500
                    """,
                    (last_rowid,),
                )
                rows = cur.fetchall()

                for row in rows:
                    event = row_to_event(row)
                    await websocket.send_json({
                        "type": "BACKFILL",
                        "event": event_to_dict(event),
                    })

                # Send READY message
                await websocket.send_json({"type": "READY", "backfill_count": len(rows)})

            finally:
                con.close()

        # Keep connection alive and handle pings
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                if message.get("type") == "PING":
                    await websocket.send_json({"type": "PONG"})
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "PING"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[websocket] Error: {e}")
        manager.disconnect(websocket)


# ─────────────────────────────────────────────────────────────────────────────
# Run server
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Starting Trading Bot API...")
    print(f"Database: {DB_PATH}")
    print(f"WebSocket endpoint: ws://localhost:8000/ws/events")
    print(f"REST API docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
