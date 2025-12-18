"""Component 7: Tradovate adapter (SIMULATED v1).

Implements the minimal interface used by the execution layer.
v1 operates in SIMULATED mode: orders are assumed filled immediately at provided price.
Live mode must obey state contract and kill-switch rules (not implemented in v1).
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


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


class TradovateAdapter:
    def __init__(self, mode: str = "SIMULATED", fill_mode: str = "IMMEDIATE"):
        if mode != "SIMULATED":
            raise NotImplementedError("Live mode not implemented in v1")
        self.mode = mode
        self.fill_mode = (fill_mode or "IMMEDIATE").upper()
        self._orders: Dict[str, OrderRecord] = {}
        self._position: int = 0
        self._last_fill_price: Optional[Decimal] = None
        self._kill_switch: bool = False
        self._event_queue: List[Dict[str, Any]] = []

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
            rec.status = "CANCELED"
            return True
        return False

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
        """Advance simulated order states for non-immediate fill modes."""
        if self.fill_mode not in ("DELAYED", "PARTIAL", "TIMEOUT"):
            return
        # Process each working/partial order
        for oid, r in list(self._orders.items()):
            if r.status in ("CANCELED", "FILLED"):
                continue
            age = (now - r.created_at).total_seconds()
            if self.fill_mode == "TIMEOUT":
                # Do nothing; rely on TTL cancellation in runner
                continue
            if self.fill_mode == "DELAYED":
                # Fill fully on first cycle after creation
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
                # First cycle → partial 50%, next → fill remainder
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

