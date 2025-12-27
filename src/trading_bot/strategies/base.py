"""
Base Strategy Interface

Defines the contract for all strategies:
1. detect(signals, beliefs, context) → bool (is setup present?)
2. plan_entry(signals, beliefs, state) → {side, size, stop, target}
3. plan_management(position, bar, beliefs) → {action, reason}
4. plan_exit(position, bar, beliefs) → {action, reason}
5. post_trade_update(outcome) → None (learning feedback)

All strategies must be stochastic (no hard-coded thresholds), calibrated to regime/TOD,
and provide full introspection for attribution and learning.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class StrategyContext:
    """Context for strategy decision-making."""
    regime: str  # "trending", "range", "volatile", "choppy"
    time_of_day: str  # "premarket", "open", "midday", "afternoon", "close"
    session_phase: int  # 0-6
    dvs: float  # Data quality score
    eqs: float  # Execution quality score
    equity_usd: Decimal
    buying_power: Decimal
    position: int  # Current position
    last_price: Decimal
    timestamp: datetime


@dataclass
class EntryPlan:
    """Planned entry for a new trade."""
    side: str  # "BUY" or "SELL"
    size: int  # Contract quantity
    entry_price: Decimal  # Target entry price (limit)
    stop_price: Decimal  # Stop loss price
    target_price: Decimal  # Take profit price
    risk_usd: Decimal  # Max risk per contract
    confidence: float  # 0.0-1.0 confidence in setup
    setup_id: str  # Internal setup identifier
    metadata: Dict[str, Any] = None


@dataclass
class ManagementAction:
    """Action to take on in-flight position."""
    action: str  # "HOLD", "TIGHTEN_STOP", "SCALE_OUT", "EXIT", "REDUCE_RISK"
    reason: str  # Why this action
    new_stop_price: Optional[Decimal] = None
    partial_exit_qty: Optional[int] = None
    metadata: Dict[str, Any] = None


@dataclass
class ExitPlan:
    """Planned exit from position."""
    action: str  # "EXIT", "PARTIAL", "HOLD"
    reason: str  # Why exiting
    exit_price: Optional[Decimal] = None
    qty: Optional[int] = None
    urgency: str = "NORMAL"  # "URGENT", "NORMAL", "PATIENT"
    metadata: Dict[str, Any] = None


@dataclass
class TradeOutcomeUpdate:
    """Learning feedback from completed trade."""
    trade_id: str
    pnl_usd: Decimal
    duration_seconds: int
    reason_exit: str
    thesis_valid: bool  # Was thesis still valid at exit?
    next_action: str  # "INCREASE_FRICTION", "LOWER_THRESHOLD", "ARCHIVE"


class Strategy(ABC):
    """
    Abstract base strategy.
    
    All strategies implement the same interface:
    1. detect() - Check if setup is present
    2. plan_entry() - Plan entry (size, stop, target)
    3. plan_management() - Manage in-flight position
    4. plan_exit() - Plan exit
    5. post_trade_update() - Learn from outcome
    """
    
    def __init__(self, name: str, template_id: str, logger=None):
        self.name = name
        self.template_id = template_id  # K1, K2, K3, K4, K5
        self.logger = logger
        self.metadata = {}
    
    @abstractmethod
    def detect(self, signals: Dict[str, Any], beliefs: Dict[str, Any], context: StrategyContext) -> bool:
        """
        Detect if setup is present.
        
        Args:
            signals: All computed signals (S1-S35)
            beliefs: All computed beliefs (F1-F6 + stability)
            context: Market context (regime, TOD, DVS, EQS, equity, etc.)
        
        Returns:
            True if setup is present and detectable now
        """
        pass
    
    @abstractmethod
    def plan_entry(self, signals: Dict[str, Any], beliefs: Dict[str, Any], context: StrategyContext) -> Optional[EntryPlan]:
        """
        Plan entry: size, stop, target.
        
        Args:
            signals: All computed signals
            beliefs: All computed beliefs
            context: Market context
        
        Returns:
            EntryPlan with side, size, stop, target, confidence, or None if cannot plan
        """
        pass
    
    @abstractmethod
    def plan_management(self, position: Dict[str, Any], bar: Dict[str, Any], beliefs: Dict[str, Any]) -> Optional[ManagementAction]:
        """
        Plan management action for in-flight position.
        
        Args:
            position: {trade_id, entry_price, qty, direction, entry_time, ...}
            bar: Current OHLCV bar
            beliefs: Current beliefs
        
        Returns:
            ManagementAction (HOLD, TIGHTEN_STOP, SCALE_OUT, EXIT) or None
        """
        pass
    
    @abstractmethod
    def plan_exit(self, position: Dict[str, Any], bar: Dict[str, Any], beliefs: Dict[str, Any]) -> Optional[ExitPlan]:
        """
        Plan exit from position.
        
        Args:
            position: {trade_id, entry_price, qty, direction, entry_time, ...}
            bar: Current OHLCV bar
            beliefs: Current beliefs
        
        Returns:
            ExitPlan (EXIT, PARTIAL, HOLD) or None
        """
        pass
    
    @abstractmethod
    def post_trade_update(self, outcome: TradeOutcomeUpdate) -> None:
        """
        Learn from completed trade outcome.
        
        Args:
            outcome: {trade_id, pnl_usd, duration, reason_exit, thesis_valid, next_action}
        
        Returns:
            None (state updated internally; learning loop feeds back to decision engine)
        """
        pass
    
    def get_introspection(self) -> Dict[str, Any]:
        """Return strategy introspection for debugging/logging."""
        return {
            "name": self.name,
            "template_id": self.template_id,
            "metadata": self.metadata,
        }


class StrategyLibrary:
    """
    Manages all strategies and provides selection/routing.
    
    Responsibilities:
    1. Load all strategy templates (K1-K5)
    2. Route detection/planning to appropriate strategy
    3. Aggregate outcomes to learning loop
    4. Provide strategy state (ACTIVE, THROTTLED, QUARANTINED)
    """
    
    def __init__(self, logger=None):
        self.logger = logger
        self.strategies: Dict[str, Strategy] = {}  # template_id -> Strategy
        self.strategy_states: Dict[str, str] = {}  # template_id -> "ACTIVE" | "THROTTLED" | "QUARANTINED"
    
    def register(self, strategy: Strategy) -> None:
        """Register a strategy."""
        self.strategies[strategy.template_id] = strategy
        self.strategy_states[strategy.template_id] = "ACTIVE"
        if self.logger:
            self.logger.info(f"Registered strategy {strategy.template_id}: {strategy.name}")
    
    def set_state(self, template_id: str, state: str) -> None:
        """Set strategy state (ACTIVE, THROTTLED, QUARANTINED)."""
        self.strategy_states[template_id] = state
        if self.logger:
            self.logger.info(f"Strategy {template_id} state → {state}")
    
    def get_state(self, template_id: str) -> str:
        """Get strategy state."""
        return self.strategy_states.get(template_id, "ACTIVE")
    
    def detect_all(self, signals: Dict[str, Any], beliefs: Dict[str, Any], context: StrategyContext) -> Dict[str, bool]:
        """Run detection on all ACTIVE strategies."""
        results = {}
        for template_id, strategy in self.strategies.items():
            if self.get_state(template_id) == "ACTIVE":
                try:
                    detected = strategy.detect(signals, beliefs, context)
                    results[template_id] = detected
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error in {template_id}.detect(): {e}")
                    results[template_id] = False
        return results
    
    def plan_entry_for(self, template_id: str, signals: Dict[str, Any], beliefs: Dict[str, Any], context: StrategyContext) -> Optional[EntryPlan]:
        """Plan entry for a specific strategy."""
        if template_id not in self.strategies:
            return None
        
        strategy = self.strategies[template_id]
        try:
            return strategy.plan_entry(signals, beliefs, context)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in {template_id}.plan_entry(): {e}")
            return None
    
    def plan_management_for(self, template_id: str, position: Dict[str, Any], bar: Dict[str, Any], beliefs: Dict[str, Any]) -> Optional[ManagementAction]:
        """Plan management for a specific strategy."""
        if template_id not in self.strategies:
            return None
        
        strategy = self.strategies[template_id]
        try:
            return strategy.plan_management(position, bar, beliefs)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in {template_id}.plan_management(): {e}")
            return None
    
    def plan_exit_for(self, template_id: str, position: Dict[str, Any], bar: Dict[str, Any], beliefs: Dict[str, Any]) -> Optional[ExitPlan]:
        """Plan exit for a specific strategy."""
        if template_id not in self.strategies:
            return None
        
        strategy = self.strategies[template_id]
        try:
            return strategy.plan_exit(position, bar, beliefs)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in {template_id}.plan_exit(): {e}")
            return None
    
    def post_trade_update(self, template_id: str, outcome: TradeOutcomeUpdate) -> None:
        """Notify strategy of trade outcome."""
        if template_id not in self.strategies:
            return
        
        strategy = self.strategies[template_id]
        try:
            strategy.post_trade_update(outcome)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in {template_id}.post_trade_update(): {e}")
    
    def get_all_states(self) -> Dict[str, str]:
        """Get all strategy states."""
        return self.strategy_states.copy()
