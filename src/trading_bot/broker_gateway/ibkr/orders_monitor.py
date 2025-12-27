"""
Orders Monitor: Subscribe to order status and fill updates from IBKR.
Translates broker events to supervisor-compatible format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Any, List, Optional
from datetime import datetime


@dataclass
class OrdersMonitor:
    _ib: Any = None
    _contract: Any = None
    _open_orders: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    _fills: List[Dict[str, Any]] = field(default_factory=list)
    _on_order_update: Optional[Callable[[Dict[str, Any]], None]] = None
    _on_fill_update: Optional[Callable[[Dict[str, Any]], None]] = None

    def set_connection(self, ib: Any, mes_contract: Any) -> None:
        """Set ib_insync connection and MES contract."""
        self._ib = ib
        self._contract = mes_contract

    def subscribe(
        self,
        on_order_update: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_fill_update: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> None:
        """Subscribe to order and fill updates."""
        self._on_order_update = on_order_update
        self._on_fill_update = on_fill_update
        
        if not self._ib:
            return
        
        try:
            # Subscribe to open orders
            self._ib.openOrderEvent += self._on_open_order
            # Subscribe to order status
            self._ib.orderStatusEvent += self._on_order_status
            # Subscribe to executions (fills)
            self._ib.execDetailsEvent += self._on_exec_details
        except Exception:
            pass

    def _on_open_order(self, trade: Any) -> None:
        """Callback when open order is received."""
        try:
            order = trade.order
            broker_id = order.orderId
            self._open_orders[broker_id] = {
                "broker_id": broker_id,
                "status": "UNKNOWN",
                "filled_qty": 0,
                "remaining": order.totalQuantity,
            }
        except Exception:
            pass

    def _on_order_status(self, trade: Any) -> None:
        """Callback when order status updates."""
        try:
            status = trade.orderStatus.status
            filled = trade.orderStatus.filled
            broker_id = trade.order.orderId
            
            self._open_orders[broker_id] = {
                "broker_id": broker_id,
                "status": status,
                "filled_qty": int(filled),
                "remaining": trade.order.totalQuantity - int(filled),
            }
            
            if self._on_order_update:
                self._on_order_update({
                    "type": "ORDER_STATUS",
                    "broker_id": broker_id,
                    "status": status,
                    "filled_qty": int(filled),
                })
        except Exception:
            pass

    def _on_exec_details(self, trade: Any, fill: Any) -> None:
        """Callback when execution/fill occurs."""
        try:
            broker_id = fill.orderId
            fill_evt = {
                "type": "FILL",
                "broker_id": broker_id,
                "filled_qty": int(fill.cumQty),
                "fill_price": float(fill.price),
                "commission": float(fill.commission or 0.0),
            }
            self._fills.append(fill_evt)
            
            if self._on_fill_update:
                self._on_fill_update(fill_evt)
        except Exception:
            pass

    def get_open_orders(self) -> Dict[int, Dict[str, Any]]:
        """Return cached open orders."""
        return dict(self._open_orders)

    def pop_fills(self) -> List[Dict[str, Any]]:
        """Pop and return all cached fills."""
        fills, self._fills = self._fills, []
        return fills

    def unsubscribe(self) -> None:
        """Unsubscribe from all events."""
        if self._ib:
            try:
                self._ib.openOrderEvent -= self._on_open_order
                self._ib.orderStatusEvent -= self._on_order_status
                self._ib.execDetailsEvent -= self._on_exec_details
            except Exception:
                pass
