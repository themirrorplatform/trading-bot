"""Component 7: Tradovate adapter (SIMULATED v1).

Implements the minimal interface used by the execution layer.
v1 operates in SIMULATED mode: orders are assumed filled immediately at provided price.
Live mode must obey state contract and kill-switch rules (not implemented in v1).
"""

from __future__ import annotations

from typing import Dict, Any, Optional
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
    def __init__(self, mode: str = "SIMULATED"):
        if mode != "SIMULATED":
            raise NotImplementedError("Live mode not implemented in v1")
        self.mode = mode
        self._orders: Dict[str, OrderRecord] = {}
        self._position: int = 0
        self._last_fill_price: Optional[Decimal] = None
        self._kill_switch: bool = False

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
            status="FILLED",
        )
        self._orders[oid] = rec
        # Update simulated position
        self._position += (intent.contracts if intent.direction == "LONG" else -intent.contracts)
        self._last_fill_price = last_price
        return {
            "order_id": oid,
            "status": rec.status,
            "filled_price": float(last_price),
            "position": self._position,
            "bracket": bracket,
        }

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

    def set_kill_switch(self, active: bool) -> None:
        self._kill_switch = bool(active)

    def get_open_orders(self) -> Dict[str, Any]:
        return {oid: {
            "direction": r.direction,
            "contracts": r.contracts,
            "status": r.status,
        } for oid, r in self._orders.items()}
