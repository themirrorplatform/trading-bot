"""
Event Publisher - Real-time sync from SQLite to Supabase.

Watches the local SQLite event store and publishes new events to Supabase
for real-time dashboard updates.

Features:
- Background thread for continuous sync
- Configurable batch size and interval
- Last-synced watermark for resumability
- Graceful degradation on Supabase errors
"""

from __future__ import annotations

import os
import time
import threading
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

from trading_bot.log.event_store import EventStore
from trading_bot.log.supabase_store import SupabaseEventStore, DecimalEncoder

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Background publisher that syncs SQLite events to Supabase.

    Usage:
        publisher = EventPublisher(
            sqlite_path="data/events.sqlite",
            supabase_url="https://xxx.supabase.co",
            supabase_key="eyJ..."
        )
        publisher.start()
        # ... trading runs ...
        publisher.stop()
    """

    def __init__(
        self,
        sqlite_path: str = "data/events.sqlite",
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        batch_size: int = 50,
        sync_interval: float = 2.0,
        watermark_file: Optional[str] = None,
    ):
        """
        Initialize event publisher.

        Args:
            sqlite_path: Path to SQLite event store
            supabase_url: Supabase project URL (or env SUPABASE_URL)
            supabase_key: Supabase service role key (or env SUPABASE_KEY)
            batch_size: Max events per sync cycle
            sync_interval: Seconds between sync cycles
            watermark_file: File to persist last-synced event ID
        """
        self.sqlite_path = sqlite_path
        self.supabase_url = supabase_url or os.environ.get("SUPABASE_URL")
        self.supabase_key = supabase_key or os.environ.get("SUPABASE_KEY")
        self.batch_size = batch_size
        self.sync_interval = sync_interval

        # Watermark for resumable sync
        self.watermark_file = watermark_file or str(
            Path(sqlite_path).parent / ".sync_watermark"
        )
        self._last_synced_id: int = 0
        self._load_watermark()

        # State
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Stats
        self._events_synced = 0
        self._errors = 0
        self._last_sync_time: Optional[datetime] = None

        # Clients (initialized on start)
        self._sqlite: Optional[EventStore] = None
        self._supabase: Optional[SupabaseEventStore] = None

    def _load_watermark(self) -> None:
        """Load last-synced event ID from file."""
        try:
            if os.path.exists(self.watermark_file):
                with open(self.watermark_file, "r") as f:
                    self._last_synced_id = int(f.read().strip() or "0")
                logger.info(f"Loaded watermark: {self._last_synced_id}")
        except Exception as e:
            logger.warning(f"Could not load watermark: {e}")
            self._last_synced_id = 0

    def _save_watermark(self) -> None:
        """Save last-synced event ID to file."""
        try:
            with open(self.watermark_file, "w") as f:
                f.write(str(self._last_synced_id))
        except Exception as e:
            logger.warning(f"Could not save watermark: {e}")

    def start(self) -> bool:
        """
        Start the background publisher thread.

        Returns:
            True if started successfully
        """
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase not available, publisher disabled")
            return False

        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase credentials not set, publisher disabled")
            return False

        try:
            # Initialize SQLite store
            self._sqlite = EventStore(self.sqlite_path)

            # Initialize Supabase store
            self._supabase = SupabaseEventStore(
                url=self.supabase_url,
                key=self.supabase_key,
            )

            self._running = True
            self._thread = threading.Thread(target=self._sync_loop, daemon=True)
            self._thread.start()

            logger.info("Event publisher started")
            return True

        except Exception as e:
            logger.error(f"Failed to start publisher: {e}")
            return False

    def stop(self) -> None:
        """Stop the publisher thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        self._save_watermark()
        logger.info(f"Event publisher stopped. Total synced: {self._events_synced}")

    def _sync_loop(self) -> None:
        """Main sync loop running in background thread."""
        while self._running:
            try:
                synced = self._sync_batch()
                if synced > 0:
                    logger.debug(f"Synced {synced} events to Supabase")

            except Exception as e:
                self._errors += 1
                logger.error(f"Sync error: {e}")

            time.sleep(self.sync_interval)

    def _sync_batch(self) -> int:
        """
        Sync a batch of events from SQLite to Supabase.

        Returns:
            Number of events synced
        """
        if not self._sqlite or not self._supabase:
            return 0

        try:
            # Query events newer than watermark
            # SQLite EventStore uses id as primary key (auto-increment)
            conn = self._sqlite._get_connection()
            cursor = conn.execute(
                """
                SELECT id, stream_id, timestamp, event_type, payload, config_hash
                FROM events
                WHERE id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (self._last_synced_id, self.batch_size)
            )

            rows = cursor.fetchall()
            if not rows:
                return 0

            # Batch insert to Supabase
            synced = 0
            max_id = self._last_synced_id

            for row in rows:
                event_id, stream_id, timestamp, event_type, payload, config_hash = row

                event = {
                    "id": event_id,
                    "stream_id": stream_id,
                    "timestamp": timestamp,
                    "event_type": event_type,
                    "payload": payload,
                    "config_hash": config_hash,
                }

                if self._supabase.append(event):
                    synced += 1
                    max_id = max(max_id, event_id)

            # Update watermark
            if synced > 0:
                with self._lock:
                    self._last_synced_id = max_id
                    self._events_synced += synced
                    self._last_sync_time = datetime.now()
                self._save_watermark()

            return synced

        except Exception as e:
            logger.error(f"Batch sync error: {e}")
            self._errors += 1
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get publisher statistics."""
        with self._lock:
            return {
                "running": self._running,
                "events_synced": self._events_synced,
                "errors": self._errors,
                "last_synced_id": self._last_synced_id,
                "last_sync_time": self._last_sync_time.isoformat() if self._last_sync_time else None,
            }

    def force_sync(self) -> int:
        """Force immediate sync (for testing/debugging)."""
        return self._sync_batch()


class TradePublisher:
    """
    Specialized publisher for trade and journal records.

    Unlike EventPublisher which syncs all events, this publishes
    denormalized trade summaries for dashboard analytics.
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
    ):
        self.supabase_url = supabase_url or os.environ.get("SUPABASE_URL")
        self.supabase_key = supabase_key or os.environ.get("SUPABASE_KEY")
        self._supabase: Optional[SupabaseEventStore] = None

        if SUPABASE_AVAILABLE and self.supabase_url and self.supabase_key:
            try:
                self._supabase = SupabaseEventStore(
                    url=self.supabase_url,
                    key=self.supabase_key,
                )
            except Exception as e:
                logger.warning(f"TradePublisher init failed: {e}")

    def publish_trade(self, trade: Dict[str, Any]) -> bool:
        """
        Publish a completed trade record.

        Args:
            trade: Trade dict with entry/exit prices, PnL, etc.

        Returns:
            True if published successfully
        """
        if not self._supabase:
            return False

        return self._supabase.insert_trade(trade)

    def publish_journal_entry(self, entry: Dict[str, Any]) -> bool:
        """
        Publish a decision journal entry.

        Args:
            entry: Journal entry dict

        Returns:
            True if published successfully
        """
        if not self._supabase:
            return False

        return self._supabase.insert_journal_entry(entry)

    def publish_daily_summary(self, summary: Dict[str, Any]) -> bool:
        """
        Publish daily trading summary.

        Args:
            summary: Daily summary dict

        Returns:
            True if published successfully
        """
        if not self._supabase:
            return False

        return self._supabase.update_daily_summary(summary)


# Convenience function for quick setup
def create_publisher(
    sqlite_path: str = "data/events.sqlite",
    auto_start: bool = True,
) -> Optional[EventPublisher]:
    """
    Create and optionally start an event publisher.

    Args:
        sqlite_path: Path to SQLite database
        auto_start: Whether to start immediately

    Returns:
        EventPublisher instance or None if Supabase unavailable
    """
    publisher = EventPublisher(sqlite_path=sqlite_path)

    if auto_start:
        if publisher.start():
            return publisher
        return None

    return publisher
