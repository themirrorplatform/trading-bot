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

    def place_order(self, intent: Any, last_price: Decimal) -> Dict[str, Any]:
        """Place an order per `OrderIntent`. In SIMULATED mode, auto-fill."""
        ts = intent.timestamp
        oid = f"SIM-{int(ts.timestamp()*1000)}"
        rec = OrderRecord(
            order_id=oid,
            ts=ts,
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
        }

    def flatten_positions(self) -> None:
        self._position = 0

    def cancel_all(self) -> None:
        for rec in self._orders.values():
            if rec.status == "NEW":
                rec.status = "CANCELED"

    def get_position_snapshot(self) -> Dict[str, Any]:
        return {
            "position": self._position,
            "last_fill_price": float(self._last_fill_price) if self._last_fill_price is not None else None,
        }
