from __future__ import annotations

from dataclasses import dataclass
from typing import List

@dataclass
class Order:
    action: str
    totalQuantity: int
    orderType: str
    lmtPrice: float | None = None
    stopPrice: float | None = None
    parentId: int | None = None
    ocaGroup: str | None = None
    orderId: int | None = None


def intent_to_ibkr_orders(intent) -> List[Order]:
    orders: List[Order] = []
    action_buy = "BUY" if getattr(intent, "direction", "LONG") == "LONG" else "SELL"
    action_sell = "SELL" if getattr(intent, "direction", "LONG") == "LONG" else "BUY"
    qty = int(getattr(intent, "contracts", getattr(intent, "quantity", 1)) or 1)
    entry_type = getattr(intent, "entry_type", "LIMIT")
    limit_price = getattr(intent, "limit_price", None)
    stop_loss = float(getattr(intent, "metadata", {}).get("bracket", {}).get("stop_price", getattr(intent, "stop_loss", 0.0)))
    take_profit = float(getattr(intent, "metadata", {}).get("bracket", {}).get("target_price", getattr(intent, "take_profit", 0.0)))
    intent_id = getattr(intent, "intent_id", "UNKNOWN")

    if entry_type == "MARKET":
        entry = Order(action=action_buy, totalQuantity=qty, orderType="MKT")
    else:
        entry = Order(action=action_buy, totalQuantity=qty, orderType="LMT", lmtPrice=limit_price)
    entry.orderId = 1

    stop = Order(action=action_sell, totalQuantity=qty, orderType="STP", stopPrice=stop_loss, parentId=entry.orderId)
    profit = Order(action=action_sell, totalQuantity=qty, orderType="LMT", lmtPrice=take_profit, parentId=entry.orderId)

    group = f"OCA_{intent_id}"
    stop.ocaGroup = group
    profit.ocaGroup = group

    orders.extend([entry, stop, profit])
    return orders
