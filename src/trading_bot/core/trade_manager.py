"""
Trade Lifecycle Manager: In-trade supervision, thesis invalidation, adaptive exits.
Manages a single open MES position through entry → management → exit → closure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from decimal import Decimal
from enum import Enum


class TradeState(Enum):
    ENTRY_PENDING = "ENTRY_PENDING"
    FILLED = "FILLED"
    MANAGING = "MANAGING"
    EXIT_TRIGGERED = "EXIT_TRIGGERED"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    ERROR = "ERROR"


@dataclass
class TradeManager:
    """Manages a single open position and its lifecycle."""
    
    trade_id: str = ""
    entry_template: str = ""  # K1, K2, K3, K4
    entry_price: Decimal = Decimal("0")
    entry_time: Optional[datetime] = None
    direction: str = "LONG"  # LONG or SHORT
    qty: int = 1
    
    # Stop and target prices (set at entry)
    stop_price: Decimal = Decimal("0")
    target_price: Decimal = Decimal("0")
    initial_risk_usd: Decimal = Decimal("0")
    
    # In-trade state
    state: TradeState = TradeState.ENTRY_PENDING
    filled_price: Optional[Decimal] = None
    filled_qty: int = 0
    filled_time: Optional[datetime] = None
    
    # Thesis invalidation signals
    thesis_invalidated: bool = False
    invalidation_reason: str = ""
    
    # Time management
    max_time_minutes: int = 30
    entry_time_check: Optional[datetime] = None
    
    # Exit tracking
    exit_time: Optional[datetime] = None
    exit_price: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    realized_pnl_pct: Optional[float] = None
    
    # Events buffer
    events: List[Dict[str, Any]] = field(default_factory=list)

    def on_fill(self, filled_qty: int, filled_price: Decimal, filled_time: datetime) -> None:
        """Handle fill notification."""
        self.filled_qty = filled_qty
        self.filled_price = filled_price
        self.filled_time = filled_time
        self.state = TradeState.FILLED
        self.entry_time_check = filled_time
        self.events.append({
            "type": "FILL",
            "qty": filled_qty,
            "price": float(filled_price),
            "ts": filled_time.isoformat(),
        })

    def tick(self, now: datetime, current_price: Decimal, market_context: Dict[str, Any]) -> Dict[str, Any]:
        """Periodic tick: check thesis, time limits, exit conditions.
        
        Returns dict with actions (exit, flatten, etc).
        """
        result = {
            "action": "HOLD",
            "reason": None,
            "exit_price": None,
        }
        
        if self.state not in (TradeState.FILLED, TradeState.MANAGING):
            return result
        
        # --- Time limit check ---
        if self.entry_time_check:
            time_in_trade = (now - self.entry_time_check).total_seconds() / 60.0  # minutes
            if time_in_trade > self.max_time_minutes:
                result["action"] = "EXIT"
                result["reason"] = f"TIME_LIMIT_EXCEEDED ({time_in_trade:.1f} min > {self.max_time_minutes} min)"
                result["exit_price"] = float(current_price)
                self.state = TradeState.EXIT_TRIGGERED
                self.events.append({
                    "type": "EXIT_TRIGGERED",
                    "reason": result["reason"],
                    "ts": now.isoformat(),
                })
                return result
        
        # --- Thesis invalidation checks ---
        # Check 1: VWAP mean reversion (K1) - if price reverses back through entry
        if self.entry_template == "K1":
            vwap_z = market_context.get("vwap_z", 0.0)
            if self.direction == "LONG" and vwap_z > 0.5:
                # Was short VWAP; now price is long of VWAP again = thesis broken
                self.thesis_invalidated = True
                self.invalidation_reason = "K1: VWAP thesis reversal (back above VWAP)"
            elif self.direction == "SHORT" and vwap_z < -0.5:
                self.thesis_invalidated = True
                self.invalidation_reason = "K1: VWAP thesis reversal (back below VWAP)"
        
        # Check 2: Range compression ended (K2) - breakout fade should have moved; if compressed again, thesis broken
        if self.entry_template == "K2":
            range_compression = market_context.get("range_compression", 1.0)
            if range_compression > 0.8:  # Range inflating again = failed breakout
                self.thesis_invalidated = True
                self.invalidation_reason = "K2: Range compressed after breakout attempt"
        
        # Check 3: Trend strength reversed (K5)
        if self.entry_template == "K4":
            hhll_trend = market_context.get("hhll_trend_strength", 0.0)
            if self.direction == "LONG" and hhll_trend < -0.5:
                self.thesis_invalidated = True
                self.invalidation_reason = "K4: Trend reversed to downtrend"
            elif self.direction == "SHORT" and hhll_trend > 0.5:
                self.thesis_invalidated = True
                self.invalidation_reason = "K4: Trend reversed to uptrend"
        
        if self.thesis_invalidated:
            result["action"] = "EXIT"
            result["reason"] = f"THESIS_INVALIDATED: {self.invalidation_reason}"
            result["exit_price"] = float(current_price)
            self.state = TradeState.EXIT_TRIGGERED
            self.events.append({
                "type": "EXIT_TRIGGERED",
                "reason": result["reason"],
                "ts": now.isoformat(),
            })
            return result
        
        # --- No exit condition met; transition to MANAGING ---
        self.state = TradeState.MANAGING
        
        return result

    def on_exit_filled(self, exit_price: Decimal, exit_time: datetime) -> None:
        """Handle exit fill."""
        self.exit_price = exit_price
        self.exit_time = exit_time
        
        # Compute PnL
        if self.filled_price:
            if self.direction == "LONG":
                pnl_ticks = (exit_price - self.filled_price) / Decimal("0.25")
                realized_pnl = pnl_ticks * Decimal("1.25")
            else:
                pnl_ticks = (self.filled_price - exit_price) / Decimal("0.25")
                realized_pnl = pnl_ticks * Decimal("1.25")
            
            self.realized_pnl = realized_pnl
            if self.initial_risk_usd > 0:
                self.realized_pnl_pct = float(realized_pnl / self.initial_risk_usd)
        
        self.state = TradeState.CLOSED
        self.events.append({
            "type": "CLOSED",
            "exit_price": float(exit_price),
            "pnl": float(self.realized_pnl or Decimal("0")),
            "ts": exit_time.isoformat(),
        })

    def pop_events(self) -> List[Dict[str, Any]]:
        """Pop and return all buffered events."""
        ev, self.events = self.events, []
        return ev
