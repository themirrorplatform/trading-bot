"""
Execution Supervisor skeleton.
Ownership:
- Order/bracket lifecycle state machine
- Idempotent submission and restart safety
- Supervision of child stop/target presence and health
- Cancel/replace, flatten, disconnect handling

States (parent):
  CREATED -> SUBMITTING -> ACKED -> PARTIAL -> FILLED -> DONE
  Failure states: REJECTED, CANCELED, ERROR
Children (stop/target) tracked per parent, must exist when parent fills.

Events expected from broker adapters:
- ORDER_ACK(order_id, broker_ids)
- ORDER_REJECT(order_id, reason)
- FILL(order_id, qty, price, avg_fill, status)
- PARTIAL_FILL(order_id, qty, price, remaining)
- CHILD_ATTACHED(parent_oid, child_type, child_oid)
- CHILD_MISSING(parent_oid, child_type)
- CANCEL_ACK(order_id)
- CANCEL_REJECT(order_id, reason)
- CONNECTION_DOWN / CONNECTION_UP

Recovery goals:
- Restart-safe via persistent run_id + client_order_id
- On reconnect: reconcile positions, open orders; repair missing children; kill switch on desync
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class ParentState(Enum):
    CREATED = auto()
    SUBMITTING = auto()
    ACKED = auto()
    PARTIAL = auto()
    FILLED = auto()
    CANCELED = auto()
    REJECTED = auto()
    ERROR = auto()
    DONE = auto()


class ChildType(Enum):
    STOP = "STOP"
    TARGET = "TARGET"


@dataclass
class ChildOrder:
    child_type: ChildType
    broker_id: Optional[str] = None
    status: str = "PENDING"
    stop_price: Optional[float] = None
    limit_price: Optional[float] = None


@dataclass
class ParentOrder:
    client_id: str  # idempotent client order id
    broker_id: Optional[str] = None
    state: ParentState = ParentState.CREATED
    direction: str = "LONG"  # LONG / SHORT
    qty: int = 0
    entry_price: Optional[float] = None
    filled_qty: int = 0
    avg_fill_price: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    children: Dict[ChildType, ChildOrder] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SupervisorEvent:
    type: str
    data: Dict[str, Any]
    ts: datetime = field(default_factory=datetime.utcnow)


class ExecutionSupervisor:
    def __init__(self):
        self._orders: Dict[str, ParentOrder] = {}
        self._events: List[SupervisorEvent] = []

    # --- Submission path ---
    def submit_intent(self, intent: Dict[str, Any], broker_adapter) -> str:
        """Create idempotent client order id, submit via adapter, track parent."""
        now = datetime.utcnow()
        client_oid = intent.get("intent_id") or f"cli-{int(now.timestamp()*1000)}-{len(self._orders)+1}"
        if client_oid in self._orders:
            # Idempotent: do not resubmit
            return client_oid
        parent = ParentOrder(
            client_id=client_oid,
            direction=intent.get("direction", "LONG"),
            qty=int(intent.get("contracts", intent.get("quantity", 1) or 1)),
            entry_price=float(intent.get("limit_price", intent.get("last_price", 0) or 0)),
            metadata={"template_id": intent.get("metadata", {}).get("template_id")}
        )
        self._orders[client_oid] = parent
        parent.state = ParentState.SUBMITTING
        self._events.append(SupervisorEvent("ORDER_SUBMIT", {"client_id": client_oid}))

        resp = broker_adapter.place_order(intent_obj=intent, last_price=intent.get("last_price"))
        # Broker adapter should be idempotent-aware, but we guard here
        status = resp.get("status") or resp.get("type")
        if status in ("ORDER_REJECTED", "REJECTED"):
            parent.state = ParentState.REJECTED
            self._events.append(SupervisorEvent("ORDER_REJECT", {"client_id": client_oid, "reason": resp.get("reason")}))
            return client_oid
        parent.broker_id = resp.get("order_id")
        parent.state = ParentState.ACKED if status in ("ACCEPTED", "SUBMITTED") else parent.state
        self._events.append(SupervisorEvent("ORDER_ACK", {"client_id": client_oid, "broker_id": parent.broker_id, "status": status}))
        return client_oid

    # --- Event handling from broker ---
    def on_broker_event(self, ev: Dict[str, Any]) -> None:
        et = ev.get("type")
        cid = ev.get("client_id") or ev.get("order_id")
        parent = self._orders.get(cid)
        if not parent:
            return
        parent.updated_at = datetime.utcnow()
        if et == "ORDER_ACK":
            parent.state = ParentState.ACKED
        elif et == "ORDER_REJECTED":
            parent.state = ParentState.REJECTED
        elif et in ("PARTIAL_FILL", "FILL"):
            fill_qty = int(ev.get("filled", 0))
            parent.filled_qty = max(parent.filled_qty, fill_qty)
            parent.avg_fill_price = ev.get("avg_fill_price", parent.avg_fill_price)
            if et == "PARTIAL_FILL":
                parent.state = ParentState.PARTIAL
            else:
                parent.state = ParentState.FILLED
        elif et == "CANCEL_ACK":
            parent.state = ParentState.CANCELED
        elif et == "CANCEL_REJECT":
            parent.state = ParentState.ERROR
        self._events.append(SupervisorEvent(et, ev))

    # --- Reconciliation ---
    def reconcile(self, broker_positions: List[Dict[str, Any]], broker_orders: List[Dict[str, Any]]) -> None:
        """Compare broker truth to local; if mismatch, emit RECONCILE_DIFF and mark ERROR."""
        # Minimal skeleton; to be expanded with idempotent repair logic
        self._events.append(SupervisorEvent("RECONCILE", {"positions": broker_positions, "orders": broker_orders}))

    # --- Flatten ---
    def flatten_all(self, broker_adapter) -> None:
        self._events.append(SupervisorEvent("FLATTEN_ALL", {}))
        try:
            broker_adapter.flatten_positions()
        except Exception as e:
            self._events.append(SupervisorEvent("FLATTEN_ERROR", {"error": str(e)}))

    # --- Tick / supervision loop ---
    def tick(self, now: datetime, ttl_seconds: int = 90) -> None:
        """Periodically enforce TTL, check missing children, and emit heartbeats."""
        self._events.append(SupervisorEvent("SUPERVISOR_HEARTBEAT", {"ts": now.isoformat()}))

    def pop_events(self) -> List[SupervisorEvent]:
        ev, self._events = self._events, []
        return ev
