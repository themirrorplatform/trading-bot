from __future__ import annotations

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import urllib.request
import urllib.error


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class NTOrderContext:
    order_id: Optional[str] = None
    status: str = "IDLE"


class NinjaTraderBridgeAdapter:
    """HTTP bridge to local NinjaTrader Add-On.

    Exposes a similar surface as TradovateAdapter so the runner can swap adapters.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8123", auth_token: str = "changeme"):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self._position: int = 0
        self._last_fill_price: Optional[float] = None
        self._event_buf: List[Dict[str, Any]] = []
        self._kill: bool = False

    # --- HTTP helpers ---
    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-Auth-Token", self.auth_token)
        try:
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                return json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.URLError:
            return {"error": True, "unreachable": True}

    def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method="GET")
        req.add_header("X-Auth-Token", self.auth_token)
        try:
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.URLError:
            return {"error": True, "unreachable": True}

    # --- Adapter interface ---
    def place_order(self, intent: Any, last_price) -> Dict[str, Any]:
        if self._kill:
            return {"order_id": None, "status": "REJECTED", "reason": "KILL_SWITCH_ACTIVE"}
        # Only limit/stop-limit supported
        entry_type = getattr(intent, "entry_type", "LIMIT").upper()
        meta = getattr(intent, "metadata", {}) or {}
        bracket = meta.get("bracket") if isinstance(meta, dict) else None
        side = "BUY" if getattr(intent, "direction", "LONG") == "LONG" else "SELL"
        qty = int(getattr(intent, "contracts", 1) or 1)
        instrument = meta.get("instrument", "ES 03-26")
        decision_id = meta.get("decision_id", f"D-{_iso_now()}")

        if entry_type == "LIMIT":
            payload = {
                "v": 1,
                "ts": _iso_now(),
                "type": "Command.EnterLimit",
                "decision_id": decision_id,
                "payload": {
                    "account": meta.get("account", "SIM101"),
                    "instrument": instrument,
                    "side": side,
                    "qty": qty,
                    "limit_price": float(meta.get("limit_price", float(last_price))),
                    "ttl_ms": int(meta.get("ttl_ms", 90000)),
                    "bracket": bracket or {},
                },
            }
        else:
            # STOP_LIMIT
            payload = {
                "v": 1,
                "ts": _iso_now(),
                "type": "Command.EnterStopLimit",
                "decision_id": decision_id,
                "payload": {
                    "account": meta.get("account", "SIM101"),
                    "instrument": instrument,
                    "side": side,
                    "qty": qty,
                    "stop_price": float(meta.get("stop_price", float(last_price))),
                    "limit_price": float(meta.get("limit_price", float(last_price))),
                    "ttl_ms": int(meta.get("ttl_ms", 90000)),
                    "bracket": bracket or {},
                },
            }
        res = self._post("/command", payload)
        # Assume bridge enqueues events; return minimal status
        return {"order_id": res.get("order_id"), "status": res.get("status", "ACCEPTED"), "bridge_ack": not res.get("error")}

    def cancel_order(self, order_id: str) -> bool:
        payload = {"v": 1, "ts": _iso_now(), "type": "Command.Cancel", "payload": {"order_id": order_id}}
        res = self._post("/command", payload)
        return not res.get("error")

    def cancel_all(self) -> None:
        # Not part of protocol v1; would need per-order cancels or a new command
        return None

    def flatten_positions(self) -> None:
        payload = {"v": 1, "ts": _iso_now(), "type": "Command.Flatten", "payload": {"account": "SIM101", "instrument": "ES 03-26"}}
        self._post("/command", payload)

    def get_position_snapshot(self) -> Dict[str, Any]:
        # Poll events to update snapshot opportunistically
        self.on_cycle(datetime.now(timezone.utc))
        return {"position": self._position, "last_fill_price": self._last_fill_price}

    def set_kill_switch(self, active: bool) -> None:
        self._kill = bool(active)

    def get_open_orders(self) -> Dict[str, Any]:
        # Bridge would need an endpoint; return empty for now
        return {}

    def on_cycle(self, now: datetime, ttl_seconds: int = 90) -> None:
        res = self._get("/events")
        if not res or res.get("error"):
            return
        # Expect either a single event object or {events:[...]}
        evts: List[Dict[str, Any]] = []
        if isinstance(res, dict) and "events" in res and isinstance(res["events"], list):
            evts = res["events"]
        elif isinstance(res, dict) and res:
            evts = [res]

        for e in evts:
            et = e.get("type") or e.get("event")
            if et in ("Event.ExecutionReport", "ExecutionReport", "FILL"):
                # Normalize to our fill payload
                fill_price = e.get("fill_price") or e.get("price")
                filled_qty = int(e.get("filled_qty") or e.get("qty") or 0)
                remaining = int(e.get("remaining_qty") or 0)
                if filled_qty:
                    # Update snapshot approximately (sign unknown without order side)
                    self._position += filled_qty  # conservative; consuming code shouldn't rely on sign here
                    self._last_fill_price = float(fill_price) if fill_price is not None else self._last_fill_price
                self._event_buf.append({
                    "type": "FILL",
                    "order_id": e.get("order_id"),
                    "filled_qty": filled_qty,
                    "fill_price": float(fill_price) if fill_price is not None else None,
                    "remaining_qty": remaining,
                    "status": e.get("state") or e.get("status") or ("PARTIAL" if remaining else "FILLED"),
                })

    def pop_events(self) -> List[Dict[str, Any]]:
        out = self._event_buf
        self._event_buf = []
        return out
