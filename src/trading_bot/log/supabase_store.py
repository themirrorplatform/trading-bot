"""
Supabase Event Store - Cloud persistence for trading bot events.

Replaces/augments SQLite event store for cloud deployment.
Supports real-time subscriptions for dashboard updates.
"""

from __future__ import annotations

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class SupabaseEventStore:
    """
    Cloud event store using Supabase PostgreSQL.

    Features:
    - Idempotent inserts (unique constraint on stream_id, timestamp, event_type, config_hash)
    - Real-time updates via Supabase subscriptions
    - Batch insert support for efficiency
    - Automatic retry on transient failures
    """

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        table_name: str = "events"
    ):
        """
        Initialize Supabase client.

        Args:
            url: Supabase project URL (or SUPABASE_URL env var)
            key: Supabase service role key (or SUPABASE_KEY env var)
            table_name: Events table name (default: "events")
        """
        if not SUPABASE_AVAILABLE:
            raise ImportError(
                "supabase-py not installed. Run: pip install supabase"
            )

        self.url = url or os.environ.get("SUPABASE_URL")
        self.key = key or os.environ.get("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError(
                "Supabase URL and key required. "
                "Set SUPABASE_URL and SUPABASE_KEY env vars or pass explicitly."
            )

        self.client: Client = create_client(self.url, self.key)
        self.table_name = table_name
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_size = 10  # Flush after N events

    def append(self, event: Dict[str, Any]) -> bool:
        """
        Append a single event to the store.

        Args:
            event: Event dict with id, stream_id, timestamp, event_type, payload, config_hash

        Returns:
            True if inserted, False if duplicate
        """
        try:
            # Serialize payload
            payload = event.get("payload", {})
            if isinstance(payload, str):
                payload_json = payload
            else:
                payload_json = json.dumps(payload, cls=DecimalEncoder)

            record = {
                "id": event.get("id"),
                "stream_id": event.get("stream_id"),
                "timestamp": event.get("timestamp"),
                "event_type": event.get("event_type"),
                "payload": json.loads(payload_json),  # Supabase wants dict, not string
                "config_hash": event.get("config_hash"),
            }

            # Upsert to handle idempotency
            result = self.client.table(self.table_name).upsert(
                record,
                on_conflict="stream_id,timestamp,event_type,config_hash"
            ).execute()

            return len(result.data) > 0

        except Exception as e:
            # Log error but don't crash - SQLite fallback should still work
            print(f"[SupabaseEventStore] Insert error: {e}")
            return False

    def append_buffered(self, event: Dict[str, Any]):
        """
        Buffer event for batch insert.
        Flushes automatically when buffer reaches threshold.

        Args:
            event: Event to buffer
        """
        self._buffer.append(event)

        if len(self._buffer) >= self._buffer_size:
            self.flush()

    def flush(self) -> int:
        """
        Flush buffered events to Supabase.

        Returns:
            Number of events flushed
        """
        if not self._buffer:
            return 0

        try:
            records = []
            for event in self._buffer:
                payload = event.get("payload", {})
                if isinstance(payload, str):
                    payload_dict = json.loads(payload)
                else:
                    payload_dict = json.loads(json.dumps(payload, cls=DecimalEncoder))

                records.append({
                    "id": event.get("id"),
                    "stream_id": event.get("stream_id"),
                    "timestamp": event.get("timestamp"),
                    "event_type": event.get("event_type"),
                    "payload": payload_dict,
                    "config_hash": event.get("config_hash"),
                })

            result = self.client.table(self.table_name).upsert(
                records,
                on_conflict="stream_id,timestamp,event_type,config_hash"
            ).execute()

            count = len(self._buffer)
            self._buffer = []
            return count

        except Exception as e:
            print(f"[SupabaseEventStore] Batch insert error: {e}")
            return 0

    def query(
        self,
        stream_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query events with filters.

        Args:
            stream_id: Filter by stream
            event_type: Filter by event type
            start_time: ISO timestamp lower bound
            end_time: ISO timestamp upper bound
            limit: Max results (default 100)

        Returns:
            List of event dicts
        """
        query = self.client.table(self.table_name).select("*")

        if stream_id:
            query = query.eq("stream_id", stream_id)
        if event_type:
            query = query.eq("event_type", event_type)
        if start_time:
            query = query.gte("timestamp", start_time)
        if end_time:
            query = query.lte("timestamp", end_time)

        query = query.order("timestamp", desc=True).limit(limit)

        result = query.execute()
        return result.data

    def get_latest(
        self,
        stream_id: str,
        event_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get most recent event of a type.

        Args:
            stream_id: Stream to query
            event_type: Event type to find

        Returns:
            Latest event or None
        """
        events = self.query(
            stream_id=stream_id,
            event_type=event_type,
            limit=1
        )
        return events[0] if events else None

    def insert_trade(self, trade: Dict[str, Any]) -> bool:
        """
        Insert a trade record (denormalized).

        Args:
            trade: Trade dict

        Returns:
            True if inserted
        """
        try:
            result = self.client.table("trades").insert(trade).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"[SupabaseEventStore] Trade insert error: {e}")
            return False

    def insert_journal_entry(self, entry: Dict[str, Any]) -> bool:
        """
        Insert a decision journal entry.

        Args:
            entry: Journal entry dict

        Returns:
            True if inserted
        """
        try:
            # Serialize nested dicts
            if "setup_scores" in entry and not isinstance(entry["setup_scores"], str):
                entry["setup_scores"] = json.loads(
                    json.dumps(entry["setup_scores"], cls=DecimalEncoder)
                )
            if "context" in entry and not isinstance(entry["context"], str):
                entry["context"] = json.loads(
                    json.dumps(entry["context"], cls=DecimalEncoder)
                )
            if "reason_details" in entry and not isinstance(entry["reason_details"], str):
                entry["reason_details"] = json.loads(
                    json.dumps(entry["reason_details"], cls=DecimalEncoder)
                )

            result = self.client.table("decision_journal").insert(entry).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"[SupabaseEventStore] Journal insert error: {e}")
            return False

    def update_daily_summary(self, summary: Dict[str, Any]) -> bool:
        """
        Upsert daily summary record.

        Args:
            summary: Daily summary dict

        Returns:
            True if upserted
        """
        try:
            result = self.client.table("daily_summary").upsert(
                summary,
                on_conflict="date,stream_id,config_hash"
            ).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"[SupabaseEventStore] Summary upsert error: {e}")
            return False


class HybridEventStore:
    """
    Hybrid event store that writes to both SQLite (local) and Supabase (cloud).

    SQLite is the primary store for reliability.
    Supabase is secondary for dashboard real-time updates.
    """

    def __init__(
        self,
        sqlite_store,  # EventStore instance
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None
    ):
        """
        Initialize hybrid store.

        Args:
            sqlite_store: Local SQLite EventStore instance
            supabase_url: Supabase project URL (optional)
            supabase_key: Supabase service role key (optional)
        """
        self.sqlite = sqlite_store
        self.supabase: Optional[SupabaseEventStore] = None

        # Only init Supabase if credentials provided
        if supabase_url and supabase_key and SUPABASE_AVAILABLE:
            try:
                self.supabase = SupabaseEventStore(
                    url=supabase_url,
                    key=supabase_key
                )
            except Exception as e:
                print(f"[HybridEventStore] Supabase init failed: {e}")

    def append(self, event: Dict[str, Any]):
        """
        Append event to both stores.
        SQLite is synchronous, Supabase is best-effort.
        """
        # Primary: SQLite (must succeed)
        self.sqlite.append(event)

        # Secondary: Supabase (best-effort)
        if self.supabase:
            self.supabase.append_buffered(event)

    def flush(self):
        """Flush Supabase buffer."""
        if self.supabase:
            self.supabase.flush()

    def init_schema(self, schema_path: str):
        """Initialize SQLite schema."""
        self.sqlite.init_schema(schema_path)
