"""Component 7: Tradovate adapter (SIM + LIVE scaffolding).

Provides a SIM adapter used by backtests and a LIVE adapter skeleton with
websocket feed + polling, heartbeats, and kill-switch hooks. The LIVE adapter is
fail-soft: it falls back to HTTP polling if `websockets` is unavailable.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

try:  # Optional dependency; live adapter will degrade to polling if missing
    import websockets  # type: ignore
except Exception:  # pragma: no cover - optional
    websockets = None


@dataclass
class OrderRecord:
    order_id: str
    ts: datetime
    created_at: datetime
    direction: str
    contracts: int
    entry_price: Decimal
    stop_ticks: int
    target_ticks: int
    status: str  # NEW, FILLED, CANCELED


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TradovateSimAdapter:
    """Simulation adapter (existing behavior)."""

    def __init__(self, mode: str = "SIMULATED", fill_mode: str = "IMMEDIATE", ttl_seconds: int = 90):
        if mode != "SIMULATED":
            raise NotImplementedError("Live mode not implemented for SIM adapter")
        self.mode = mode
        self.fill_mode = (fill_mode or "IMMEDIATE").upper()
        self.ttl_seconds = int(ttl_seconds)
        self._orders: Dict[str, OrderRecord] = {}
        self._position: int = 0
        self._last_fill_price: Optional[Decimal] = None
        self._kill_switch: bool = False
        self._event_queue: List[Dict[str, Any]] = []
        self._mods: Dict[str, int] = {}

    def place_order(self, intent: Any, last_price: Decimal) -> Dict[str, Any]:
        """Place an order per `OrderIntent`. In SIMULATED mode, enforce safety and auto-fill when valid."""
        if self._kill_switch:
            return {"order_id": None, "status": "REJECTED", "reason": "KILL_SWITCH_ACTIVE"}

        entry_type = getattr(intent, "entry_type", "MARKET")
        meta = getattr(intent, "metadata", {}) or {}
        bracket = meta.get("bracket") if isinstance(meta, dict) else None
        if entry_type not in ("LIMIT", "STOP_LIMIT"):
            return {"order_id": None, "status": "REJECTED", "reason": "NO_MARKET_ENTRIES"}
        if not isinstance(bracket, dict) or "stop_price" not in bracket or "target_price" not in bracket:
            return {"order_id": None, "status": "REJECTED", "reason": "BRACKET_REQUIRED"}

        ts = intent.timestamp
        oid = f"SIM-{int(ts.timestamp()*1000)}"
        rec = OrderRecord(
            order_id=oid,
            ts=ts,
            created_at=ts,
            direction=intent.direction,
            contracts=intent.contracts,
            entry_price=last_price,
            stop_ticks=intent.stop_ticks,
            target_ticks=intent.target_ticks,
            status="FILLED" if self.fill_mode == "IMMEDIATE" else "WORKING",
        )
        self._orders[oid] = rec
        result = {"order_id": oid, "status": rec.status, "bracket": bracket}
        if rec.status == "FILLED":
            # Immediate fill
            delta = intent.contracts if intent.direction == "LONG" else -intent.contracts
            self._position += delta
            self._last_fill_price = last_price
            result.update({"filled_price": float(last_price), "position": self._position, "filled_delta": delta})
            # enqueue a fill event for runner to consume
            self._event_queue.append({
                "type": "FILL",
                "order_id": oid,
                "filled_qty": abs(delta),
                "fill_price": float(last_price),
                "remaining_qty": 0,
                "status": "FILLED",
            })
        else:
            # Working order (DELAYED/PARTIAL/TIMEOUT)
            result.update({"position": self._position, "filled_delta": 0})
        return result

    def flatten_positions(self) -> None:
        self._position = 0

    def cancel_all(self) -> None:
        for rec in self._orders.values():
            if rec.status == "NEW":
                rec.status = "CANCELED"

    def cancel_order(self, order_id: str) -> bool:
        rec = self._orders.get(order_id)
        if not rec:
            return False
        if rec.status in ("NEW", "WORKING", "ACCEPTED"):
            # modification budget check
            mc = self._mods.get(order_id, 0)
            if mc >= 2:
                return False
            rec.status = "CANCELED"
            self._mods[order_id] = mc + 1
            return True
        return False

    def replace_order(self, order_id: str, new_meta: Dict[str, Any]) -> Dict[str, Any]:
        rec = self._orders.get(order_id)
        if not rec:
            return {"ok": False, "reason": "ORDER_NOT_FOUND"}
        if rec.status not in ("NEW", "WORKING", "PARTIAL"):
            return {"ok": False, "reason": "ORDER_NOT_MODIFIABLE"}
        mc = self._mods.get(order_id, 0)
        if mc >= 2:
            return {"ok": False, "reason": "MODIFICATION_LIMIT_EXCEEDED"}
        # For SIM, only adjust entry_price if limit_price provided
        lp = new_meta.get("limit_price")
        if lp is not None:
            try:
                rec.entry_price = Decimal(str(lp))
            except Exception:
                pass
        self._mods[order_id] = mc + 1
        return {"ok": True, "order_id": order_id, "modifications": self._mods[order_id]}

    def get_position_snapshot(self) -> Dict[str, Any]:
        return {
            "position": self._position,
            "last_fill_price": float(self._last_fill_price) if self._last_fill_price is not None else None,
        }

    def set_kill_switch(self, active: bool) -> None:
        # SIM: no-op aside from internal flag
        self._kill_switch = bool(active)

    def get_open_orders(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for oid, r in self._orders.items():
            out[oid] = {
                "status": r.status,
                "direction": r.direction,
                "contracts": r.contracts,
                "created_at": r.created_at.isoformat(),
            }
        return out

    # --- Simulation time advancement ---
    def on_cycle(self, now: datetime, ttl_seconds: int = 90) -> None:
        """Advance simulated order states for non-immediate fill modes and TTL cancels."""
        # TTL enforcement for working orders
        for oid, r in list(self._orders.items()):
            if r.status in ("CANCELED", "FILLED"):
                continue
            age = (now - r.created_at).total_seconds()
            if age > max(self.ttl_seconds, int(ttl_seconds)) and r.status in ("NEW", "WORKING", "ACCEPTED", "PARTIAL"):
                mc = self._mods.get(oid, 0)
                if mc < 2:
                    r.status = "CANCELED"
                    self._mods[oid] = mc + 1
                continue

        if self.fill_mode not in ("DELAYED", "PARTIAL", "TIMEOUT"):
            return
        for oid, r in list(self._orders.items()):
            if r.status in ("CANCELED", "FILLED"):
                continue
            if self.fill_mode == "TIMEOUT":
                continue
            if self.fill_mode == "DELAYED":
                r.status = "FILLED"
                delta = r.contracts if r.direction == "LONG" else -r.contracts
                self._position += delta
                self._last_fill_price = r.entry_price
                self._event_queue.append({
                    "type": "FILL",
                    "order_id": oid,
                    "filled_qty": abs(delta),
                    "fill_price": float(r.entry_price),
                    "remaining_qty": 0,
                    "status": "FILLED",
                })
            elif self.fill_mode == "PARTIAL":
                half = max(1, int(r.contracts // 2))
                if r.status == "WORKING":
                    r.status = "PARTIAL"
                    delta = half if r.direction == "LONG" else -half
                    self._position += delta
                    self._last_fill_price = r.entry_price
                    self._event_queue.append({
                        "type": "FILL",
                        "order_id": oid,
                        "filled_qty": abs(delta),
                        "fill_price": float(r.entry_price),
                        "remaining_qty": r.contracts - abs(delta),
                        "status": "PARTIAL",
                    })
                elif r.status == "PARTIAL":
                    rem = r.contracts - half
                    delta = rem if r.direction == "LONG" else -rem
                    r.status = "FILLED"
                    self._position += delta
                    self._last_fill_price = r.entry_price
                    self._event_queue.append({
                        "type": "FILL",
                        "order_id": oid,
                        "filled_qty": abs(delta),
                        "fill_price": float(r.entry_price),
                        "remaining_qty": 0,
                        "status": "FILLED",
                    })

    def pop_events(self) -> List[Dict[str, Any]]:
        evts = self._event_queue
        self._event_queue = []
        return evts


class TradovateLiveAdapter:
    """Live adapter with order state tracking and slippage telemetry.

    Network operations are best-effort and fail-soft to avoid blocking the
    runner. Websocket support is optional (requires the `websockets` package).
    
    Order States: PENDING → WORKING → FILLED/CANCELED/REJECTED
    """

    def __init__(
        self,
        api_url: str = "https://live.tradovateapi.com/v1",
        ws_url: Optional[str] = None,
        account_id: Optional[int] = None,
        access_token: Optional[str] = None,
        instrument: str = "MES",
        heartbeat_interval: int = 10,
        reconnect_interval: int = 20,
        poll_interval: int = 5,
    ):
        self.mode = "LIVE"
        self.api_url = api_url.rstrip("/")
        self.ws_url = ws_url.rstrip("/") if ws_url else None
        self.account_id = account_id
        self.access_token = access_token
        self.instrument = instrument
        self.heartbeat_interval = heartbeat_interval
        self.reconnect_interval = reconnect_interval
        self.poll_interval = poll_interval

        self._orders: Dict[str, Dict[str, Any]] = {}
        self._position: int = 0
        self._last_fill_price: Optional[float] = None
        self._kill_switch: bool = False
        self._event_queue: List[Dict[str, Any]] = []
        self._last_heartbeat: float = 0.0
        self._last_ws_message: float = 0.0
        self._last_poll: float = 0.0
        self._mods: Dict[str, int] = {}
        self._ttl_seconds: int = 90
        # State tracking for reconciliation
        self._order_states: Dict[str, str] = {}  # oid → state

        # Websocket background worker
        self._ws_thread: Optional[threading.Thread] = None
        self._ws_stop = threading.Event()
        if self.ws_url and websockets is not None:
            self._start_ws()

    # --- HTTP helpers ---
    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.access_token:
            h["Authorization"] = f"Bearer {self.access_token}"
        return h

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.api_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                body = resp.read().decode("utf-8") or "{}"
                return json.loads(body)
        except urllib.error.URLError:
            return {"error": True, "unreachable": True}

    def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self.api_url}{path}"
        req = urllib.request.Request(url, method="GET", headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                body = resp.read().decode("utf-8") or "{}"
                return json.loads(body)
        except urllib.error.URLError:
            return {"error": True, "unreachable": True}

    # --- Websocket worker ---
    def _start_ws(self) -> None:
        if self._ws_thread and self._ws_thread.is_alive():
            return
        self._ws_stop.clear()
        self._ws_thread = threading.Thread(target=self._ws_worker, name="tradovate-ws", daemon=True)
        self._ws_thread.start()

    def _ws_worker(self) -> None:
        if websockets is None:
            return
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._ws_loop())

    async def _ws_loop(self) -> None:
        assert websockets is not None
        while not self._ws_stop.is_set():
            try:
                async with websockets.connect(self.ws_url, extra_headers=self._headers()) as ws:  # type: ignore
                    # Subscribe to order and market data streams (symbol-level)
                    sub_msg = json.dumps({"type": "subscribe", "channel": "orders", "instrument": self.instrument})
                    await ws.send(sub_msg)
                    md_msg = json.dumps({"type": "subscribe", "channel": "md", "instrument": self.instrument})
                    await ws.send(md_msg)
                    self._last_heartbeat = time.time()
                    self._last_ws_message = time.time()
                    async for raw in ws:
                        self._last_ws_message = time.time()
                        self._last_heartbeat = time.time()
                        self._handle_ws_message(raw)
            except Exception:
                # Backoff before reconnect
                await asyncio.sleep(self.reconnect_interval)

    def _handle_ws_message(self, raw: Any) -> None:
        try:
            msg = json.loads(raw)
        except Exception:
            return
        etype = msg.get("type") or msg.get("event")
        oid = msg.get("order_id")
        
        if etype in ("fill", "order.fill", "FILL"):
            fill_price = msg.get("fill_price") or msg.get("price")
            filled_qty = int(msg.get("filled_qty") or msg.get("qty") or 0)
            remaining = int(msg.get("remaining_qty") or 0)
            
            # State transition: WORKING → PARTIAL or FILLED
            if oid:
                new_state = "PARTIAL" if remaining else "FILLED"
                self._order_states[oid] = new_state
            
            if filled_qty:
                self._position += filled_qty
                self._last_fill_price = float(fill_price) if fill_price is not None else self._last_fill_price
            
            # Slippage telemetry: compare fill vs limit
            slippage_ticks = 0.0
            if oid and fill_price is not None:
                od = self._orders.get(oid, {})
                limit_price = od.get("limit_price")
                if limit_price is not None:
                    tick_size = 0.25  # MES tick
                    direction = 1 if od.get("direction") == "BUY" else -1
                    slippage_ticks = direction * (float(fill_price) - float(limit_price)) / tick_size
            
            self._event_queue.append({
                "type": "FILL",
                "order_id": oid,
                "filled_qty": filled_qty,
                "fill_price": float(fill_price) if fill_price is not None else None,
                "remaining_qty": remaining,
                "status": msg.get("state") or msg.get("status") or ("PARTIAL" if remaining else "FILLED"),
                "slippage_ticks": slippage_ticks,
            })
        elif etype in ("order.working", "WORKING"):
            # State transition: PENDING → WORKING
            if oid:
                self._order_states[oid] = "WORKING"
        elif etype in ("order.canceled", "CANCELED", "order.rejected", "REJECTED"):
            # State transition: * → CANCELED/REJECTED
            if oid:
                self._order_states[oid] = etype.split(".")[-1].upper()
        elif etype in ("heartbeat", "ping"):
            self._last_heartbeat = time.time()

    # --- Adapter surface ---
    def place_order(self, intent: Any, last_price: Decimal | float) -> Dict[str, Any]:
        if self._kill_switch:
            return {"order_id": None, "status": "REJECTED", "reason": "KILL_SWITCH_ACTIVE"}

        entry_type = getattr(intent, "entry_type", "LIMIT").upper()
        meta = getattr(intent, "metadata", {}) or {}
        bracket = meta.get("bracket") if isinstance(meta, dict) else None
        side = "BUY" if getattr(intent, "direction", "LONG") == "LONG" else "SELL"
        qty = int(getattr(intent, "contracts", 1) or 1)
        limit_price = float(meta.get("limit_price", last_price))
        stop_price = meta.get("stop_price")
        ttl_ms = int(meta.get("ttl_ms", 90000))

        payload: Dict[str, Any] = {
            "accountId": self.account_id,
            "instrument": meta.get("instrument", self.instrument),
            "side": side,
            "qty": qty,
            "type": entry_type,
            "limitPrice": limit_price,
            "ttlMs": ttl_ms,
            "bracket": bracket or {},
        }
        if entry_type == "STOP_LIMIT" and stop_price is not None:
            payload["stopPrice"] = float(stop_price)

        res = self._post("/orders/place", payload)
        order_id = res.get("orderId") or res.get("order_id")
        status = res.get("status") or ("ACCEPTED" if not res.get("error") else "REJECTED")
        if order_id:
            oid_str = str(order_id)
            # Explicit state: PENDING → WORKING (or REJECTED)
            initial_state = "PENDING" if status == "ACCEPTED" else status
            self._order_states[oid_str] = initial_state
            self._orders[oid_str] = {
                "status": status,
                "state": initial_state,
                "direction": side,
                "contracts": qty,
                "created_at": _iso_now(),
                "modifications": 0,
                "limit_price": limit_price,
            }
        return {"order_id": order_id, "status": status, "broker_ack": not res.get("error"), "reason": res.get("reason")}

    def cancel_all(self) -> None:
        for oid in list(self._orders.keys()):
            try:
                self.cancel_order(oid)
            except Exception:
                continue

    def cancel_order(self, order_id: str) -> bool:
        mc = self._mods.get(order_id, 0)
        if mc >= 2:
            return False
        res = self._post("/orders/cancel", {"orderId": order_id, "accountId": self.account_id})
        ok = not res.get("error")
        if ok and order_id in self._orders:
            self._orders[order_id]["status"] = "CANCELED"
            self._mods[order_id] = mc + 1
            self._orders[order_id]["modifications"] = self._mods[order_id]
        return ok

    def replace_order(self, order_id: str, new_meta: Dict[str, Any]) -> Dict[str, Any]:
        mc = self._mods.get(order_id, 0)
        if mc >= 2:
            return {"ok": False, "reason": "MODIFICATION_LIMIT_EXCEEDED"}
        payload = {"orderId": order_id, "accountId": self.account_id}
        if "limit_price" in new_meta:
            payload["limitPrice"] = float(new_meta["limit_price"])
        if "stop_price" in new_meta:
            payload["stopPrice"] = float(new_meta["stop_price"])
        res = self._post("/orders/replace", payload)
        if res.get("error"):
            return {"ok": False, "reason": "BROKER_ERROR"}
        self._mods[order_id] = mc + 1
        if order_id in self._orders:
            self._orders[order_id]["modifications"] = self._mods[order_id]
        return {"ok": True, "order_id": order_id, "modifications": self._mods[order_id]}

    def flatten_positions(self) -> None:
        self._post("/positions/flatten", {"accountId": self.account_id, "instrument": self.instrument})

    def get_position_snapshot(self) -> Dict[str, Any]:
        res = self._get(f"/accounts/{self.account_id}/positions") if self.account_id else {}
        # Expect format: {positions:[{instrument, netPos, avgPrice}]}
        if isinstance(res, dict):
            positions = res.get("positions") or res.get("data") or []
            for p in positions:
                if p.get("instrument") == self.instrument:
                    self._position = int(p.get("netPos") or p.get("position") or 0)
                    ap = p.get("avgPrice")
                    if ap is not None:
                        try:
                            self._last_fill_price = float(ap)
                        except Exception:
                            pass
                    break
        return {"position": self._position, "last_fill_price": self._last_fill_price}

    def set_kill_switch(self, active: bool) -> None:
        self._kill_switch = bool(active)
        if active:
            try:
                self.cancel_all()
            except Exception:
                pass

    def get_open_orders(self) -> Dict[str, Any]:
        # Opportunistic refresh when polling
        return self._orders
    
    def get_order_states(self) -> Dict[str, str]:
        """Return explicit order states for reconciliation."""
        return self._order_states.copy()

    def _poll_orders(self) -> None:
        res = self._get(f"/accounts/{self.account_id}/orders") if self.account_id else {}
        if not isinstance(res, dict):
            return
        orders = res.get("orders") or res.get("data") or []
        for o in orders:
            oid = str(o.get("orderId") or o.get("id"))
            status = o.get("status") or o.get("state")
            if oid:
                # Map broker status to our state
                state_map = {
                    "Accepted": "PENDING",
                    "Working": "WORKING",
                    "Filled": "FILLED",
                    "Canceled": "CANCELED",
                    "Rejected": "REJECTED",
                }
                state = state_map.get(status, status.upper() if status else "UNKNOWN")
                self._order_states[oid] = state
                
                self._orders[oid] = {
                    "status": status,
                    "state": state,
                    "direction": o.get("side"),
                    "contracts": o.get("qty"),
                    "created_at": o.get("time") or o.get("created_at") or _iso_now(),
                    "modifications": self._mods.get(oid, 0),
                    "limit_price": o.get("limitPrice"),
                }
            if status in ("Filled", "FILLED"):
                # Compute slippage if possible
                slippage_ticks = 0.0
                fill_price = o.get("avgFillPrice")
                limit_price = o.get("limitPrice")
                if fill_price and limit_price:
                    tick_size = 0.25
                    direction = 1 if o.get("side") == "BUY" else -1
                    slippage_ticks = direction * (float(fill_price) - float(limit_price)) / tick_size
                
                self._event_queue.append({
                    "type": "FILL",
                    "order_id": oid,
                    "filled_qty": int(o.get("qty") or 0),
                    "fill_price": float(fill_price) if fill_price else None,
                    "remaining_qty": 0,
                    "status": "FILLED",
                    "slippage_ticks": slippage_ticks,
                })

    def on_cycle(self, now: datetime, ttl_seconds: int = 90) -> None:
        now_ts = time.time()
        # TTL cancels for working orders
        self._ttl_seconds = int(ttl_seconds)
        for oid, od in list(self._orders.items()):
            st = (od.get("status") or "").upper()
            if st in ("CANCELED", "FILLED"):
                continue
            try:
                created_at = datetime.fromisoformat(str(od.get("created_at")))
            except Exception:
                created_at = datetime.now(timezone.utc)
            age = (now - created_at).total_seconds()
            if age > self._ttl_seconds and st in ("NEW", "WORKING", "ACCEPTED", "PARTIAL"):
                # respect modification cap
                if self._mods.get(oid, 0) < 2:
                    try:
                        self.cancel_order(oid)
                    except Exception:
                        pass
        # Restart websocket if stale
        if self.ws_url and websockets is not None:
            stale = (now_ts - self._last_ws_message) > self.reconnect_interval if self._last_ws_message else False
            if stale:
                self._ws_stop.set()
                self._start_ws()

        # Heartbeat watchdog: if no heartbeat, set kill-switch
        if self.heartbeat_interval and (now_ts - self._last_heartbeat) > (self.heartbeat_interval * 2):
            self._kill_switch = True

        # Poll broker for orders/positions if enough time passed (fallback when no WS)
        if (now_ts - self._last_poll) >= self.poll_interval:
            self._last_poll = now_ts
            try:
                self._poll_orders()
            except Exception:
                pass
            try:
                self.get_position_snapshot()
            except Exception:
                pass

    def pop_events(self) -> List[Dict[str, Any]]:
        evts = self._event_queue
        self._event_queue = []
        return evts


# Backward compatibility alias for existing SIM usage
TradovateAdapter = TradovateSimAdapter


