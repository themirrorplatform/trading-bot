from __future__ import annotations

from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field

# Canonical Event Schemas (Section 12)

class MarketBarClosed(BaseModel):
    timestamp: str
    symbol: Literal["MES"]
    timeframe: Literal["1m"]
    open: float
    high: float
    low: float
    close: float
    volume: int
    dvs: float = Field(ge=0.0, le=1.0)
    dvs_penalties: List[str] = Field(default_factory=list)

class MarketSessionState(BaseModel):
    state: Literal["PRE", "OPEN", "CLOSED"]
    timestamp: str

class DecisionRecordEvent(BaseModel):
    timestamp: str
    signals: Dict[str, float]
    beliefs: Dict[str, float]
    eligible_templates: List[str]
    scores: Dict[str, float]
    decision: Literal["TRADE", "NO_TRADE"]
    reason: str
    selected_template: Optional[str]

class OrderIntentCreated(BaseModel):
    intent_id: str
    direction: Literal["LONG", "SHORT"]
    quantity: int
    entry_type: Literal["MARKET", "LIMIT"]
    limit_price: Optional[float]
    stop_loss: float
    take_profit: float
    template_id: str
    reason_vector: Dict[str, Any]

class OrderIntentRejected(BaseModel):
    intent_id: str
    reason: str
    constitutional_state: Dict[str, Any]

class OrderSubmitted(BaseModel):
    intent_id: str
    broker_order_id: str
    timestamp: str

class OrderAck(BaseModel):
    broker_order_id: str
    status: str
    timestamp: str

class OrderRejected(BaseModel):
    broker_order_id: str
    reason: str
    timestamp: str

class FillPartial(BaseModel):
    broker_order_id: str
    filled_qty: int
    remaining_qty: int
    fill_price: float
    timestamp: str

class FillComplete(BaseModel):
    broker_order_id: str
    total_qty: int
    avg_fill_price: float
    slippage_ticks: int
    timestamp: str

class AccountSnapshot(BaseModel):
    equity: float
    buying_power: float
    daily_pnl: float
    timestamp: str

class PositionSnapshotEvent(BaseModel):
    symbol: str
    quantity: int
    avg_price: float
    unrealized_pnl: float
    timestamp: str

class TradeClosed(BaseModel):
    trade_id: str
    entry_price: float
    exit_price: float
    pnl: float
    r_multiple: float
    exit_reason: str
    bars_held: int
    timestamp: str

class AttributionResult(BaseModel):
    trade_id: str
    category: str  # A0-A9
    confidence: float
    learning_target: str
    detail: str

class ModelUpdate(BaseModel):
    parameter: str
    old_value: float
    new_value: float
    trigger: str  # attribution category
    mode: Literal["shadow", "live"]
    timestamp: str
