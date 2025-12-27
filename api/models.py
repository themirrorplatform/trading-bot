"""Data models for Trading Bot API."""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MarketContext(BaseModel):
    """Market state at decision time."""
    connected: bool
    session_open: bool
    execution_enabled: bool
    data_mode: str  # LIVE, DELAYED, HISTORICAL_ONLY, NONE
    data_quality: str  # GOOD, DELAYED, HISTORICAL_ONLY
    last_tick_ts: Optional[float] = None
    last_hist_bar_ts: Optional[float] = None
    primary_contract: Optional[str] = None
    dte: Optional[int] = None
    contract_month: Optional[str] = None


class SignalState(BaseModel):
    """Signal state at decision time."""
    signal_name: str
    value: float
    threshold: float
    is_triggered: bool
    regime: Optional[str] = None


class BeliefState(BaseModel):
    """Belief about market direction."""
    bias: str  # BULLISH, BEARISH, NEUTRAL
    confidence: float  # 0.0 to 1.0
    reason: Optional[str] = None


class DecisionEvent(BaseModel):
    """Decision event from trading bot."""
    timestamp: datetime
    timestamp_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    contract: str
    decision: str  # BUY, SELL, HOLD, CLOSE_LONG, CLOSE_SHORT
    position_size: Optional[float] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason_code: str  # WHY_BIAS_TRIGGER, WHY_SIGNAL_CROSSOVER, etc.
    signals: Dict[str, SignalState]
    belief: BeliefState
    market_context: MarketContext
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-12-27T12:00:00Z",
                "contract": "MES",
                "decision": "BUY",
                "position_size": 2,
                "entry_price": 6750.50,
                "reason_code": "WHY_BIAS_TRIGGER",
                "signals": {},
                "belief": {"bias": "BULLISH", "confidence": 0.75},
                "market_context": {"connected": True, "session_open": True}
            }
        }


class PositionUpdate(BaseModel):
    """Position open/close update."""
    timestamp: datetime
    timestamp_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    contract: str
    action: str  # OPEN, UPDATE, CLOSE
    position_size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: Optional[float] = None
    days_held: Optional[int] = None
    status: str  # OPEN, CLOSED_PROFIT, CLOSED_LOSS
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ReadinessSnapshot(BaseModel):
    """Market readiness assessment."""
    timestamp: datetime
    timestamp_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    contract: str
    now_et: str
    dte: Optional[int] = None
    levels: Dict[str, float] = {}  # PDH, PDL, PDC, ONH, ONL, VWAP_PROXY
    distances: Dict[str, float] = {}  # points, atr
    atr_proxy: Optional[float] = None
    realized_vol_proxy: Optional[float] = None
    trend_slope_proxy: Optional[float] = None
    regime: Optional[str] = None  # TREND, CHOP
    data_quality: str
    levels_available: bool
    vwap_method: str  # VOLUME_WEIGHTED or SIMPLE_MEAN
    last_close: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class ExecutionError(BaseModel):
    """Execution error event."""
    timestamp: datetime
    timestamp_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    contract: str
    error_type: str  # GATE_BLOCKED, ORDER_REJECTED, MARGIN_CALL, etc.
    message: str
    severity: str  # ERROR, WARNING, CRITICAL
    blocked_reason: Optional[str] = None  # WHY the gate was closed
    metadata: Optional[Dict[str, Any]] = None


class BotStatus(BaseModel):
    """Current bot status."""
    timestamp: datetime
    timestamp_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    adapter: str  # ibkr, binance, simulation
    mode: str  # LIVE, DEMO, BACKTEST
    connected: bool
    account_equity: Optional[float] = None
    primary_contract: Optional[str] = None
    execution_enabled: bool
    session_open: bool
    data_quality: str
    error_message: Optional[str] = None


class LearningRecord(BaseModel):
    """Learning record after trade close."""
    timestamp: datetime
    timestamp_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    contract: str
    trade_id: str
    signal_correlations: Dict[str, float] = {}  # signal_name -> correlation_score
    best_signal: Optional[str] = None
    worst_signal: Optional[str] = None
    pnl: float
    pnl_percent: float
    duration_bars: int
    metadata: Optional[Dict[str, Any]] = None
