"""
Data Feed Client - Real-time market data from Tradovate.

Provides:
- WebSocket connection to Tradovate market data
- 1-minute bar aggregation from ticks
- OHLCV bar callbacks for the trading loop
- Automatic reconnection and heartbeat

Alternative data sources can be added (e.g., NinjaTrader, direct CME feed).
"""

from __future__ import annotations

import os
import json
import time
import asyncio
import threading
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from collections import deque
from enum import Enum

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

logger = logging.getLogger(__name__)


class BarInterval(Enum):
    """Supported bar intervals."""
    TICK = "tick"
    SECOND_1 = "1s"
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"


@dataclass
class Bar:
    """OHLCV bar data structure."""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    tick_count: int = 0
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": self.timestamp.isoformat(),
            "o": float(self.open),
            "h": float(self.high),
            "l": float(self.low),
            "c": float(self.close),
            "v": self.volume,
            "tick_count": self.tick_count,
            "bid": float(self.bid) if self.bid else None,
            "ask": float(self.ask) if self.ask else None,
        }


@dataclass
class Tick:
    """Single tick/trade data."""
    timestamp: datetime
    price: Decimal
    size: int
    side: str = "UNKNOWN"  # BID, ASK, or UNKNOWN


class BarAggregator:
    """
    Aggregates ticks into OHLCV bars.

    Supports minute-boundary bars for trading loop.
    """

    def __init__(
        self,
        interval: BarInterval = BarInterval.MINUTE_1,
        on_bar: Optional[Callable[[Bar], None]] = None,
    ):
        self.interval = interval
        self.on_bar = on_bar

        # Current bar being built
        self._current_bar: Optional[Bar] = None
        self._current_minute: Optional[int] = None

        # Recent bars for signal engine
        self._bars: deque = deque(maxlen=500)

        # Latest bid/ask
        self._bid: Optional[Decimal] = None
        self._ask: Optional[Decimal] = None

    def process_tick(self, tick: Tick) -> Optional[Bar]:
        """
        Process a tick and potentially emit a completed bar.

        Args:
            tick: Incoming tick data

        Returns:
            Completed bar if minute boundary crossed, None otherwise
        """
        ts = tick.timestamp
        minute = ts.minute

        # Check if we need to close current bar
        completed_bar = None
        if self._current_bar and self._current_minute != minute:
            completed_bar = self._finalize_bar()

        # Initialize new bar if needed
        if not self._current_bar:
            self._current_bar = Bar(
                timestamp=ts.replace(second=0, microsecond=0),
                open=tick.price,
                high=tick.price,
                low=tick.price,
                close=tick.price,
                volume=tick.size,
                tick_count=1,
            )
            self._current_minute = minute
        else:
            # Update current bar
            self._current_bar.high = max(self._current_bar.high, tick.price)
            self._current_bar.low = min(self._current_bar.low, tick.price)
            self._current_bar.close = tick.price
            self._current_bar.volume += tick.size
            self._current_bar.tick_count += 1

        return completed_bar

    def process_quote(self, bid: Decimal, ask: Decimal) -> None:
        """Update bid/ask spread."""
        self._bid = bid
        self._ask = ask
        if self._current_bar:
            self._current_bar.bid = bid
            self._current_bar.ask = ask

    def _finalize_bar(self) -> Bar:
        """Finalize and emit current bar."""
        bar = self._current_bar
        bar.bid = self._bid
        bar.ask = self._ask

        self._bars.append(bar)

        if self.on_bar:
            self.on_bar(bar)

        self._current_bar = None
        self._current_minute = None

        return bar

    def get_bars(self, count: int = 100) -> List[Bar]:
        """Get recent bars."""
        return list(self._bars)[-count:]

    def get_current_bar(self) -> Optional[Bar]:
        """Get the bar currently being built."""
        return self._current_bar


class TradovateDataFeed:
    """
    Real-time market data from Tradovate WebSocket.

    Connects to Tradovate market data WebSocket and aggregates
    ticks into 1-minute bars for the trading loop.
    """

    def __init__(
        self,
        access_token: str,
        symbol: str = "MESZ4",
        environment: str = "demo",
        on_bar: Optional[Callable[[Bar], None]] = None,
        on_tick: Optional[Callable[[Tick], None]] = None,
        on_quote: Optional[Callable[[Decimal, Decimal], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize Tradovate data feed.

        Args:
            access_token: Tradovate access token (from live adapter auth)
            symbol: Symbol to subscribe to (e.g., MESZ4)
            environment: "demo" or "live"
            on_bar: Callback for completed bars
            on_tick: Callback for each tick
            on_quote: Callback for bid/ask updates
            on_error: Callback for errors
        """
        self.access_token = access_token
        self.symbol = symbol
        self.environment = environment

        # WebSocket URL
        if environment == "live":
            self.ws_url = "wss://md.tradovateapi.com/v1/websocket"
        else:
            self.ws_url = "wss://md-demo.tradovateapi.com/v1/websocket"

        # Callbacks
        self.on_bar = on_bar
        self.on_tick = on_tick
        self.on_quote = on_quote
        self.on_error = on_error

        # Bar aggregator
        self.aggregator = BarAggregator(on_bar=on_bar)

        # State
        self._running = False
        self._connected = False
        self._ws: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None
        self._subscription_id: Optional[int] = None
        self._request_id: int = 1

        # Latest quote
        self._bid: Optional[Decimal] = None
        self._ask: Optional[Decimal] = None

    def start(self) -> bool:
        """
        Start the data feed in a background thread.

        Returns:
            True if started successfully
        """
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets library not installed")
            return False

        self._running = True
        self._thread = threading.Thread(target=self._run_async, daemon=True)
        self._thread.start()

        logger.info(f"Data feed starting for {self.symbol}")
        return True

    def stop(self) -> None:
        """Stop the data feed."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("Data feed stopped")

    def _run_async(self) -> None:
        """Run async event loop in thread."""
        asyncio.run(self._connect_and_stream())

    async def _connect_and_stream(self) -> None:
        """Connect to WebSocket and stream data."""
        retry_count = 0
        max_retries = 10

        while self._running and retry_count < max_retries:
            try:
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=30,
                    ping_timeout=10,
                ) as ws:
                    self._ws = ws
                    self._connected = True
                    retry_count = 0

                    logger.info("Data feed WebSocket connected")

                    # Authenticate
                    await self._authenticate()

                    # Subscribe to market data
                    await self._subscribe()

                    # Listen for messages
                    async for message in ws:
                        if not self._running:
                            break
                        await self._handle_message(message)

            except Exception as e:
                self._connected = False
                retry_count += 1
                wait_time = min(2 ** retry_count, 60)

                logger.error(f"Data feed error: {e}, retrying in {wait_time}s")
                if self.on_error:
                    self.on_error(str(e))

                if self._running:
                    await asyncio.sleep(wait_time)

        self._connected = False

    async def _authenticate(self) -> None:
        """Authenticate WebSocket connection."""
        auth_msg = f"authorize\n{self._request_id}\n\n{self.access_token}"
        self._request_id += 1
        await self._ws.send(auth_msg)

        # Wait for auth response
        response = await self._ws.recv()
        if "error" in response.lower():
            raise Exception(f"Auth failed: {response}")

        logger.info("Data feed authenticated")

    async def _subscribe(self) -> None:
        """Subscribe to market data for symbol."""
        # Get contract ID for symbol
        get_contract_msg = f"md/getChart\n{self._request_id}\n\n" + json.dumps({
            "symbol": self.symbol,
            "chartDescription": {
                "underlyingType": "Tick",
                "elementSize": 1,
                "elementSizeUnit": "UnderlyingUnits",
            },
            "timeRange": {
                "asMuchAsElements": 1,
            },
        })
        self._subscription_id = self._request_id
        self._request_id += 1
        await self._ws.send(get_contract_msg)

        logger.info(f"Subscribed to {self.symbol}")

    async def _handle_message(self, message: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            # Tradovate messages: event\nid\n\njson
            parts = message.split("\n", 3)
            if len(parts) < 4:
                return

            event_type = parts[0]
            payload = json.loads(parts[3]) if parts[3] else {}

            if event_type == "md/chart":
                self._handle_chart_data(payload)
            elif event_type == "md/quote":
                self._handle_quote(payload)
            elif event_type == "md/dom":
                self._handle_dom(payload)

        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.error(f"Message handling error: {e}")

    def _handle_chart_data(self, data: Dict[str, Any]) -> None:
        """Handle chart/tick data."""
        bars = data.get("bars", [])

        for bar_data in bars:
            # Each "bar" in tick subscription is a single tick
            timestamp_ms = bar_data.get("timestamp")
            if timestamp_ms:
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            price = Decimal(str(bar_data.get("close", 0)))
            volume = int(bar_data.get("volume", 1))

            tick = Tick(
                timestamp=timestamp,
                price=price,
                size=volume,
            )

            # Callback for raw tick
            if self.on_tick:
                self.on_tick(tick)

            # Aggregate into bars
            completed_bar = self.aggregator.process_tick(tick)

    def _handle_quote(self, data: Dict[str, Any]) -> None:
        """Handle quote (bid/ask) update."""
        quotes = data.get("quotes", [data])

        for q in quotes:
            bid = q.get("bid")
            ask = q.get("ask")

            if bid is not None:
                self._bid = Decimal(str(bid))
            if ask is not None:
                self._ask = Decimal(str(ask))

            if self._bid and self._ask:
                self.aggregator.process_quote(self._bid, self._ask)

                if self.on_quote:
                    self.on_quote(self._bid, self._ask)

    def _handle_dom(self, data: Dict[str, Any]) -> None:
        """Handle DOM (depth of market) update."""
        # Extract top of book for spread calculation
        bids = data.get("bids", [])
        asks = data.get("asks", [])

        if bids:
            self._bid = Decimal(str(bids[0].get("price", 0)))
        if asks:
            self._ask = Decimal(str(asks[0].get("price", 0)))

        if self._bid and self._ask:
            self.aggregator.process_quote(self._bid, self._ask)

    def is_connected(self) -> bool:
        """Check if feed is connected."""
        return self._connected

    def get_bars(self, count: int = 100) -> List[Bar]:
        """Get recent aggregated bars."""
        return self.aggregator.get_bars(count)

    def get_current_bar(self) -> Optional[Bar]:
        """Get bar currently being built."""
        return self.aggregator.get_current_bar()

    def get_spread(self) -> Optional[Decimal]:
        """Get current bid/ask spread in ticks."""
        if self._bid and self._ask:
            return (self._ask - self._bid) / Decimal("0.25")
        return None


class SimulatedDataFeed:
    """
    Simulated data feed for testing and replay.

    Replays historical bars from CSV or generates synthetic data.
    """

    def __init__(
        self,
        bars: List[Dict[str, Any]],
        speed: float = 1.0,
        on_bar: Optional[Callable[[Bar], None]] = None,
    ):
        """
        Initialize simulated feed.

        Args:
            bars: List of bar dicts with ts, o, h, l, c, v
            speed: Playback speed multiplier (1.0 = real-time)
            on_bar: Callback for each bar
        """
        self.bars = bars
        self.speed = speed
        self.on_bar = on_bar

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._current_index = 0

    def start(self) -> bool:
        """Start simulated feed."""
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        """Stop simulated feed."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run_loop(self) -> None:
        """Run bar emission loop."""
        interval = 60.0 / self.speed  # 1 minute bars

        while self._running and self._current_index < len(self.bars):
            bar_dict = self.bars[self._current_index]

            bar = Bar(
                timestamp=datetime.fromisoformat(bar_dict["ts"]),
                open=Decimal(str(bar_dict["o"])),
                high=Decimal(str(bar_dict["h"])),
                low=Decimal(str(bar_dict["l"])),
                close=Decimal(str(bar_dict["c"])),
                volume=int(bar_dict.get("v", 0)),
                bid=Decimal(str(bar_dict.get("bid", bar_dict["c"]))),
                ask=Decimal(str(bar_dict.get("ask", bar_dict["c"]))),
            )

            if self.on_bar:
                self.on_bar(bar)

            self._current_index += 1
            time.sleep(interval)

    def is_connected(self) -> bool:
        return self._running

    def get_progress(self) -> float:
        """Get replay progress as percentage."""
        if not self.bars:
            return 100.0
        return (self._current_index / len(self.bars)) * 100.0
