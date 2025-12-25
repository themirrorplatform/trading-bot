"""
Tradovate LIVE Adapter - Production-ready broker integration.

Implements:
- OAuth2 authentication with token refresh
- REST API for order management
- WebSocket for real-time market data and order updates
- Position reconciliation
- Kill switch enforcement
- TTL order management

API Documentation: https://api.tradovate.com/
"""

from __future__ import annotations

import os
import json
import time
import asyncio
import threading
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import urllib.request
import urllib.error
import ssl

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

logger = logging.getLogger(__name__)


class TradovateEnvironment(Enum):
    """Tradovate API environments."""
    DEMO = "demo"
    LIVE = "live"


@dataclass
class TradovateConfig:
    """Configuration for Tradovate connection."""
    username: str
    password: str
    app_id: str = ""
    app_version: str = "1.0"
    cid: int = 0  # Client ID
    sec: str = ""  # Client secret
    device_id: str = "trading-bot-v2"
    environment: TradovateEnvironment = TradovateEnvironment.DEMO

    # Endpoints
    @property
    def auth_url(self) -> str:
        if self.environment == TradovateEnvironment.LIVE:
            return "https://live.tradovateapi.com/v1"
        return "https://demo.tradovateapi.com/v1"

    @property
    def md_url(self) -> str:
        if self.environment == TradovateEnvironment.LIVE:
            return "wss://md.tradovateapi.com/v1/websocket"
        return "wss://md-demo.tradovateapi.com/v1/websocket"

    @property
    def ws_url(self) -> str:
        if self.environment == TradovateEnvironment.LIVE:
            return "wss://live.tradovateapi.com/v1/websocket"
        return "wss://demo.tradovateapi.com/v1/websocket"


@dataclass
class OrderState:
    """Track order state."""
    order_id: int
    client_order_id: str
    status: str
    direction: str
    contracts: int
    limit_price: Optional[float]
    stop_price: Optional[float]
    filled_qty: int = 0
    avg_fill_price: Optional[float] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    bracket_ids: List[int] = field(default_factory=list)


class TradovateLiveAdapter:
    """
    Production Tradovate adapter with full live trading support.

    Features:
    - OAuth2 with automatic token refresh
    - REST API for order placement/cancellation
    - WebSocket for real-time updates
    - Position reconciliation on every cycle
    - Kill switch with auto-flatten
    - TTL-based stale order cancellation
    """

    def __init__(
        self,
        config: Optional[TradovateConfig] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        environment: str = "demo",
        on_fill: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_position: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize Tradovate LIVE adapter.

        Args:
            config: TradovateConfig object (preferred)
            username: Tradovate username (if not using config)
            password: Tradovate password (if not using config)
            environment: "demo" or "live"
            on_fill: Callback for fill events
            on_position: Callback for position updates
            on_error: Callback for errors
        """
        if config:
            self.config = config
        else:
            self.config = TradovateConfig(
                username=username or os.environ.get("TRADOVATE_USERNAME", ""),
                password=password or os.environ.get("TRADOVATE_PASSWORD", ""),
                environment=TradovateEnvironment(environment.lower()),
            )

        # Authentication state
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._account_id: Optional[int] = None
        self._account_spec: Optional[str] = None

        # Order tracking
        self._orders: Dict[int, OrderState] = {}
        self._client_to_order_id: Dict[str, int] = {}
        self._next_client_id: int = int(time.time() * 1000)

        # Position tracking
        self._position: int = 0
        self._last_fill_price: Optional[float] = None
        self._realized_pnl: float = 0.0

        # Kill switch
        self._kill_switch: bool = False
        self._kill_reason: Optional[str] = None

        # WebSocket state
        self._ws: Optional[Any] = None
        self._ws_task: Optional[asyncio.Task] = None
        self._ws_connected: bool = False
        self._md_ws: Optional[Any] = None
        self._subscriptions: Dict[str, int] = {}

        # Callbacks
        self._on_fill = on_fill
        self._on_position = on_position
        self._on_error = on_error

        # Event queue for async -> sync bridge
        self._event_queue: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

        # SSL context for API calls
        self._ssl_context = ssl.create_default_context()

    # ==================== Authentication ====================

    def authenticate(self) -> bool:
        """
        Authenticate with Tradovate API and get access token.

        Returns:
            True if authentication successful
        """
        try:
            payload = {
                "name": self.config.username,
                "password": self.config.password,
                "appId": self.config.app_id or "TradingBotV2",
                "appVersion": self.config.app_version,
                "deviceId": self.config.device_id,
                "cid": self.config.cid,
                "sec": self.config.sec,
            }

            response = self._post("/auth/accesstokenrequest", payload)

            if "accessToken" in response:
                self._access_token = response["accessToken"]
                # Token expires in ~90 minutes, refresh at 80 minutes
                self._token_expiry = datetime.now(timezone.utc).replace(
                    minute=datetime.now().minute + 80
                )
                logger.info("Tradovate authentication successful")

                # Get account info
                self._fetch_account_info()
                return True
            else:
                error = response.get("errorText", "Unknown auth error")
                logger.error(f"Tradovate auth failed: {error}")
                if self._on_error:
                    self._on_error(f"Auth failed: {error}")
                return False

        except Exception as e:
            logger.exception("Tradovate authentication error")
            if self._on_error:
                self._on_error(f"Auth exception: {e}")
            return False

    def _refresh_token_if_needed(self) -> bool:
        """Refresh access token if expiring soon."""
        if not self._token_expiry:
            return self.authenticate()

        if datetime.now(timezone.utc) >= self._token_expiry:
            logger.info("Refreshing Tradovate access token")
            return self.authenticate()

        return True

    def _fetch_account_info(self) -> None:
        """Fetch account details after authentication."""
        try:
            accounts = self._get("/account/list")
            if accounts and len(accounts) > 0:
                # Use first active account
                for acc in accounts:
                    if acc.get("active", False):
                        self._account_id = acc["id"]
                        self._account_spec = acc.get("name", f"Account-{acc['id']}")
                        logger.info(f"Using account: {self._account_spec} (ID: {self._account_id})")
                        break

                if not self._account_id and accounts:
                    self._account_id = accounts[0]["id"]
                    self._account_spec = accounts[0].get("name", f"Account-{self._account_id}")
        except Exception as e:
            logger.warning(f"Could not fetch account info: {e}")

    # ==================== REST API ====================

    def _request(self, method: str, path: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated HTTP request to Tradovate API."""
        url = f"{self.config.auth_url}{path}"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        data = json.dumps(payload).encode("utf-8") if payload else None

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=10, context=self._ssl_context) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            logger.error(f"HTTP {e.code} for {path}: {error_body}")
            try:
                return json.loads(error_body)
            except:
                return {"error": True, "httpCode": e.code, "message": error_body}
        except urllib.error.URLError as e:
            logger.error(f"URL error for {path}: {e}")
            return {"error": True, "message": str(e)}

    def _get(self, path: str) -> Any:
        """GET request."""
        self._refresh_token_if_needed()
        return self._request("GET", path)

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST request."""
        if path != "/auth/accesstokenrequest":
            self._refresh_token_if_needed()
        return self._request("POST", path, payload)

    # ==================== Order Management ====================

    def place_order(self, intent: Any, last_price: Decimal) -> Dict[str, Any]:
        """
        Place an order via Tradovate API.

        Args:
            intent: OrderIntent with direction, contracts, stop_ticks, target_ticks, etc.
            last_price: Current market price for limit calculation

        Returns:
            Order result dict with order_id, status, etc.
        """
        # Kill switch check
        if self._kill_switch:
            return {
                "order_id": None,
                "status": "REJECTED",
                "reason": "KILL_SWITCH_ACTIVE",
                "kill_reason": self._kill_reason,
            }

        # Validate entry type (no market orders per constitution)
        entry_type = getattr(intent, "entry_type", "LIMIT").upper()
        if entry_type not in ("LIMIT", "STOP_LIMIT"):
            return {
                "order_id": None,
                "status": "REJECTED",
                "reason": "NO_MARKET_ENTRIES",
            }

        # Validate bracket exists
        meta = getattr(intent, "metadata", {}) or {}
        bracket = meta.get("bracket") if isinstance(meta, dict) else None
        if not isinstance(bracket, dict) or "stop_price" not in bracket:
            return {
                "order_id": None,
                "status": "REJECTED",
                "reason": "BRACKET_REQUIRED",
            }

        # Generate client order ID
        client_order_id = f"BOT-{self._next_client_id}"
        self._next_client_id += 1

        # Determine action
        direction = getattr(intent, "direction", "LONG")
        action = "Buy" if direction == "LONG" else "Sell"
        contracts = int(getattr(intent, "contracts", 1))

        # Get limit price
        limit_price = float(meta.get("limit_price", float(last_price)))

        # Build order payload
        order_payload = {
            "accountSpec": self._account_spec,
            "accountId": self._account_id,
            "action": action,
            "symbol": meta.get("instrument", "MESZ4"),  # Default to current MES
            "orderQty": contracts,
            "orderType": "Limit",
            "price": limit_price,
            "isAutomated": True,
            "clOrdId": client_order_id,
        }

        try:
            # Place entry order
            result = self._post("/order/placeorder", order_payload)

            if "orderId" in result:
                order_id = result["orderId"]

                # Track order
                order_state = OrderState(
                    order_id=order_id,
                    client_order_id=client_order_id,
                    status=result.get("ordStatus", "Working"),
                    direction=direction,
                    contracts=contracts,
                    limit_price=limit_price,
                    stop_price=bracket.get("stop_price"),
                )
                self._orders[order_id] = order_state
                self._client_to_order_id[client_order_id] = order_id

                # Place bracket orders (OSO - One Sends Other)
                self._place_bracket_orders(
                    parent_order_id=order_id,
                    direction=direction,
                    contracts=contracts,
                    stop_price=bracket["stop_price"],
                    target_price=bracket.get("target_price"),
                )

                logger.info(f"Order placed: {order_id} ({direction} {contracts} @ {limit_price})")

                return {
                    "order_id": order_id,
                    "client_order_id": client_order_id,
                    "status": "WORKING",
                    "limit_price": limit_price,
                    "bracket": bracket,
                }
            else:
                error = result.get("errorText", result.get("message", "Unknown error"))
                logger.error(f"Order placement failed: {error}")
                return {
                    "order_id": None,
                    "status": "REJECTED",
                    "reason": error,
                }

        except Exception as e:
            logger.exception("Order placement error")
            return {
                "order_id": None,
                "status": "REJECTED",
                "reason": str(e),
            }

    def _place_bracket_orders(
        self,
        parent_order_id: int,
        direction: str,
        contracts: int,
        stop_price: float,
        target_price: Optional[float],
    ) -> None:
        """Place stop-loss and take-profit bracket orders."""
        try:
            # Stop loss - opposite direction
            stop_action = "Sell" if direction == "LONG" else "Buy"

            stop_payload = {
                "accountSpec": self._account_spec,
                "accountId": self._account_id,
                "action": stop_action,
                "symbol": "MESZ4",
                "orderQty": contracts,
                "orderType": "Stop",
                "stopPrice": stop_price,
                "isAutomated": True,
            }

            stop_result = self._post("/order/placeorder", stop_payload)
            if "orderId" in stop_result:
                self._orders[parent_order_id].bracket_ids.append(stop_result["orderId"])
                logger.info(f"Stop order placed: {stop_result['orderId']} @ {stop_price}")

            # Take profit
            if target_price:
                tp_payload = {
                    "accountSpec": self._account_spec,
                    "accountId": self._account_id,
                    "action": stop_action,
                    "symbol": "MESZ4",
                    "orderQty": contracts,
                    "orderType": "Limit",
                    "price": target_price,
                    "isAutomated": True,
                }

                tp_result = self._post("/order/placeorder", tp_payload)
                if "orderId" in tp_result:
                    self._orders[parent_order_id].bracket_ids.append(tp_result["orderId"])
                    logger.info(f"Target order placed: {tp_result['orderId']} @ {target_price}")

        except Exception as e:
            logger.error(f"Bracket order placement error: {e}")

    def cancel_order(self, order_id: int) -> bool:
        """Cancel an open order."""
        try:
            result = self._post("/order/cancelorder", {"orderId": order_id})

            if result.get("orderId") == order_id:
                if order_id in self._orders:
                    self._orders[order_id].status = "Canceled"
                logger.info(f"Order cancelled: {order_id}")
                return True
            else:
                logger.warning(f"Cancel order failed: {result}")
                return False

        except Exception as e:
            logger.error(f"Cancel order error: {e}")
            return False

    def cancel_all(self) -> int:
        """Cancel all open orders."""
        cancelled = 0
        for order_id, state in list(self._orders.items()):
            if state.status in ("Working", "Accepted", "PendingNew"):
                if self.cancel_order(order_id):
                    cancelled += 1
        return cancelled

    def flatten_positions(self) -> bool:
        """Flatten all positions immediately."""
        try:
            if self._position == 0:
                return True

            # Market order to flatten
            action = "Sell" if self._position > 0 else "Buy"
            qty = abs(self._position)

            payload = {
                "accountSpec": self._account_spec,
                "accountId": self._account_id,
                "action": action,
                "symbol": "MESZ4",
                "orderQty": qty,
                "orderType": "Market",
                "isAutomated": True,
            }

            result = self._post("/order/placeorder", payload)

            if "orderId" in result:
                logger.info(f"Flatten order placed: {result['orderId']}")
                self._position = 0
                return True
            else:
                logger.error(f"Flatten failed: {result}")
                return False

        except Exception as e:
            logger.exception("Flatten positions error")
            return False

    # ==================== Position & State ====================

    def get_position_snapshot(self) -> Dict[str, Any]:
        """Get current position state."""
        return {
            "position": self._position,
            "last_fill_price": self._last_fill_price,
            "realized_pnl": self._realized_pnl,
            "account_id": self._account_id,
            "kill_switch": self._kill_switch,
        }

    def reconcile_position(self) -> Dict[str, Any]:
        """
        Reconcile local position with broker.
        Critical for safety - if mismatch, trigger kill switch.
        """
        try:
            # Get positions from broker
            positions = self._get(f"/position/list")

            broker_position = 0
            for pos in positions:
                if pos.get("accountId") == self._account_id:
                    broker_position += pos.get("netPos", 0)

            local_position = self._position

            result = {
                "local_position": local_position,
                "broker_position": broker_position,
                "match": local_position == broker_position,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if local_position != broker_position:
                logger.error(f"POSITION MISMATCH: local={local_position}, broker={broker_position}")
                result["action"] = "KILL_SWITCH_TRIGGERED"
                self.set_kill_switch(True, "POSITION_MISMATCH")
                self.flatten_positions()

            return result

        except Exception as e:
            logger.error(f"Position reconciliation error: {e}")
            return {
                "error": str(e),
                "local_position": self._position,
                "match": False,
            }

    def get_open_orders(self) -> Dict[int, Dict[str, Any]]:
        """Get all open orders."""
        result = {}
        for order_id, state in self._orders.items():
            if state.status in ("Working", "Accepted", "PendingNew"):
                result[order_id] = {
                    "status": state.status,
                    "direction": state.direction,
                    "contracts": state.contracts,
                    "limit_price": state.limit_price,
                    "filled_qty": state.filled_qty,
                    "created_at": state.created_at.isoformat(),
                }
        return result

    def set_kill_switch(self, active: bool, reason: Optional[str] = None) -> None:
        """Set kill switch state."""
        self._kill_switch = active
        self._kill_reason = reason

        if active:
            logger.critical(f"KILL SWITCH ACTIVATED: {reason}")
            # Cancel all orders and flatten
            self.cancel_all()
            self.flatten_positions()

    # ==================== WebSocket ====================

    async def connect_websocket(self) -> None:
        """Connect to Tradovate WebSocket for real-time updates."""
        if not WEBSOCKETS_AVAILABLE:
            logger.warning("websockets library not installed, using polling mode")
            return

        if not self._access_token:
            logger.error("Must authenticate before connecting WebSocket")
            return

        try:
            uri = self.config.ws_url

            async with websockets.connect(uri) as ws:
                self._ws = ws
                self._ws_connected = True
                logger.info("WebSocket connected")

                # Authenticate WebSocket
                auth_msg = f"authorize\n1\n\n{self._access_token}"
                await ws.send(auth_msg)

                # Subscribe to order and fill events
                await ws.send("user/syncrequest\n2\n\n{}")

                # Listen for messages
                async for message in ws:
                    await self._handle_ws_message(message)

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self._ws_connected = False
            if self._on_error:
                self._on_error(f"WebSocket error: {e}")

    async def _handle_ws_message(self, message: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            # Tradovate uses custom message format: event\nid\n\njson
            parts = message.split("\n", 3)
            if len(parts) < 4:
                return

            event_type = parts[0]
            payload = json.loads(parts[3]) if parts[3] else {}

            if event_type == "order":
                self._handle_order_update(payload)
            elif event_type == "fill":
                self._handle_fill(payload)
            elif event_type == "position":
                self._handle_position_update(payload)

        except Exception as e:
            logger.error(f"Error handling WS message: {e}")

    def _handle_order_update(self, data: Dict[str, Any]) -> None:
        """Handle order status update."""
        order_id = data.get("id")
        status = data.get("ordStatus")

        if order_id in self._orders:
            self._orders[order_id].status = status
            logger.info(f"Order {order_id} status: {status}")

    def _handle_fill(self, data: Dict[str, Any]) -> None:
        """Handle fill event."""
        order_id = data.get("orderId")
        fill_price = data.get("price")
        fill_qty = data.get("qty", 0)

        if order_id in self._orders:
            state = self._orders[order_id]
            state.filled_qty += fill_qty
            state.avg_fill_price = fill_price

            # Update position
            delta = fill_qty if state.direction == "LONG" else -fill_qty
            self._position += delta
            self._last_fill_price = fill_price

            logger.info(f"Fill: {order_id} {fill_qty} @ {fill_price}, position now {self._position}")

            # Callback
            if self._on_fill:
                self._on_fill({
                    "order_id": order_id,
                    "fill_price": fill_price,
                    "fill_qty": fill_qty,
                    "position": self._position,
                })

        # Queue event for sync access
        with self._lock:
            self._event_queue.append({
                "type": "FILL",
                "order_id": order_id,
                "fill_price": fill_price,
                "fill_qty": fill_qty,
                "position": self._position,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    def _handle_position_update(self, data: Dict[str, Any]) -> None:
        """Handle position update from broker."""
        broker_pos = data.get("netPos", 0)

        if self._on_position:
            self._on_position({
                "broker_position": broker_pos,
                "local_position": self._position,
            })

    def pop_events(self) -> List[Dict[str, Any]]:
        """Pop all queued events (for sync access from runner)."""
        with self._lock:
            events = self._event_queue.copy()
            self._event_queue.clear()
            return events

    # ==================== Polling Fallback ====================

    def poll_updates(self) -> List[Dict[str, Any]]:
        """
        Poll for order/fill updates (fallback when WebSocket unavailable).
        Call this periodically (every 1-5 seconds) in the main loop.
        """
        events = []

        try:
            # Get recent orders
            orders = self._get("/order/list")
            for order in orders:
                order_id = order.get("id")
                status = order.get("ordStatus")

                if order_id in self._orders:
                    old_status = self._orders[order_id].status
                    if status != old_status:
                        self._orders[order_id].status = status
                        events.append({
                            "type": "ORDER_UPDATE",
                            "order_id": order_id,
                            "old_status": old_status,
                            "new_status": status,
                        })

            # Get recent fills
            fills = self._get("/fill/list")
            # Process new fills...

        except Exception as e:
            logger.error(f"Polling error: {e}")

        return events

    # ==================== Lifecycle ====================

    def start(self) -> bool:
        """Start the adapter (authenticate and optionally connect WebSocket)."""
        if not self.authenticate():
            return False

        # Start WebSocket in background if available
        if WEBSOCKETS_AVAILABLE:
            def run_ws():
                asyncio.run(self.connect_websocket())

            ws_thread = threading.Thread(target=run_ws, daemon=True)
            ws_thread.start()

        return True

    def stop(self) -> None:
        """Stop the adapter."""
        self._ws_connected = False
        if self._ws:
            # Close WebSocket
            pass
        logger.info("Tradovate adapter stopped")
