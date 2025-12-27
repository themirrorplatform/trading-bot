"""
Learning Loop with Throttling and Quarantine

Captures trade outcomes, computes reliability metrics, and adjusts strategy thresholds.
- Reliability Models: Win rate, expectancy, Sharpe, max drawdown per strategy/regime/TOD
- Confidence Calibration: Lower thresholds if win rate drops below min_acceptable
- Throttling: Increase friction (EUC cost) for underperforming strategies
- Quarantine: Disable strategy on 2+ consecutive losses or negative expectancy
- Re-enable: Strategy re-enabled on 2+ consecutive wins or recovery signal
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
import json


class StrategyState(Enum):
    """Strategy operational state."""
    ACTIVE = "ACTIVE"
    THROTTLED = "THROTTLED"
    QUARANTINED = "QUARANTINED"
    ARCHIVED = "ARCHIVED"


@dataclass
class TradeOutcome:
    """Captured trade outcome for learning."""
    trade_id: str
    template_id: str  # K1, K2, K3, K4
    regime: str  # e.g., "trending", "range", "volatile"
    time_of_day: str  # e.g., "premarket", "open", "midday", "close"
    entry_price: Decimal
    exit_price: Decimal
    qty: int
    entry_time: datetime
    exit_time: datetime
    pnl_usd: Decimal
    pnl_pct: Decimal
    duration_seconds: int
    reason_exit: str  # "THESIS_INVALID", "TIME_LIMIT", "VOL_LIMIT", "MANUAL", "STOP", "TARGET"
    beliefs_at_entry: Dict[str, float]  # {constraint_id: likelihood}
    signals_at_entry: Dict[str, float]  # {signal_id: value}
    setup_scores: Dict[str, float]  # {constraint_id: score}
    euc_score: float
    data_quality: float  # DVS
    execution_quality: float  # EQS
    slippage_ticks: float
    spread_ticks: float
    slippage_expected_ticks: float = 0.5  # Model prediction for slippage
    commission_round_trip: Decimal = Decimal("2.50")  # MES round-trip commission
    win: bool = False  # True if pnl_usd > 0
    
    @property
    def actual_pnl_usd(self) -> Decimal:
        """
        PnL after deducting round-trip commission.
        
        Commission is deducted from gross PnL to calculate net return.
        """
        return self.pnl_usd - self.commission_round_trip


@dataclass
class ReliabilityMetrics:
    """Reliability metrics for a strategy in a specific regime/TOD."""
    strategy_key: str  # "{template_id}_{regime}_{tod}"
    template_id: str
    regime: str
    time_of_day: str
    
    trades_count: int = 0
    wins: int = 0
    losses: int = 0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    
    total_pnl: Decimal = Decimal("0")
    avg_pnl: Decimal = Decimal("0")
    expectancy: Decimal = Decimal("0")  # E[PnL] per trade
    
    pnl_std: Decimal = Decimal("0")  # Standard deviation of PnL
    sharpe_ratio: float = 0.0  # Expectancy / std(PnL)
    max_drawdown: Decimal = Decimal("0")
    win_rate: float = 0.0  # wins / trades_count
    loss_rate: float = 0.0
    
    avg_duration: int = 0  # seconds
    avg_slippage: float = 0.0  # ticks
    avg_spread: float = 0.0  # ticks
    
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    # Throttle state
    throttle_level: int = 0  # 0 = normal, 1 = mild throttle, 2 = heavy throttle
    throttle_reason: str = ""
    state: StrategyState = StrategyState.ACTIVE
    state_change_reason: str = ""
    
    def update_from_trade(self, outcome: TradeOutcome) -> None:
        """Update metrics from a single trade outcome."""
        self.trades_count += 1
        
        if outcome.win:
            self.wins += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.losses += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        
        # Weight PnL contribution by data quality (repurposed as weight):
        # LIVE ~1.0, DELAYED ~0.4, HISTORICAL_ONLY ~0.0
        try:
            weight = float(getattr(outcome, "data_quality", 1.0) or 1.0)
        except Exception:
            weight = 1.0
        self.total_pnl += (outcome.pnl_usd * Decimal(str(weight)))
        self.avg_pnl = self.total_pnl / Decimal(self.trades_count)
        self.expectancy = self.avg_pnl
        self.win_rate = float(self.wins) / self.trades_count if self.trades_count > 0 else 0.0
        self.loss_rate = float(self.losses) / self.trades_count if self.trades_count > 0 else 0.0
        
        self.last_updated = datetime.utcnow()
    
    def should_quarantine(self, min_acceptable_win_rate: float = 0.40) -> Tuple[bool, str]:
        """Check if strategy should be quarantined."""
        # Quarantine on 2+ consecutive losses
        if self.consecutive_losses >= 2:
            return True, "CONSECUTIVE_LOSSES"
        
        # Quarantine if expectancy is negative after 5+ trades
        if self.trades_count >= 5 and self.expectancy < 0:
            return True, "NEGATIVE_EXPECTANCY"
        
        # Quarantine if win rate drops below min_acceptable after 10+ trades
        if self.trades_count >= 10 and self.win_rate < min_acceptable_win_rate:
            return True, "LOW_WIN_RATE"
        
        return False, ""
    
    def should_re_enable(self) -> Tuple[bool, str]:
        """Check if quarantined strategy should be re-enabled."""
        # Re-enable on 2+ consecutive wins
        if self.consecutive_wins >= 2:
            return True, "RECOVERY_WINS"
        
        # Re-enable on positive expectancy after reset window
        if self.trades_count >= 3 and self.expectancy > 0:
            return True, "POSITIVE_EXPECTANCY"
        
        return False, ""
    
    def compute_throttle_level(self, min_acceptable_win_rate: float = 0.40) -> int:
        """Compute throttle level based on current metrics."""
        if self.trades_count < 3:
            return 0  # Not enough data
        
        # Mild throttle: win rate 30–40%
        if self.win_rate < min_acceptable_win_rate and self.win_rate >= 0.30:
            return 1
        
        # Heavy throttle: win rate 20–30%
        if self.win_rate >= 0.20 and self.win_rate < 0.30:
            return 2
        
        # Still active: win rate >= 40%
        return 0


class LearningLoop:
    """
    Manages strategy reliability tracking, calibration, and throttling.
    
    Responsibilities:
    1. Capture trade outcomes (entry/exit, PnL, duration, reason)
    2. Update reliability metrics per strategy/regime/TOD
    3. Check quarantine conditions and apply/lift quarantines
    4. Compute throttle levels for underperforming strategies
    5. Adjust EUC cost modifiers in decision engine based on throttle
    6. Log learning events for audit trail
    """
    
    def __init__(self, logger=None):
        self.logger = logger
        self.metrics: Dict[str, ReliabilityMetrics] = {}  # strategy_key -> ReliabilityMetrics
        self.trade_history: List[TradeOutcome] = []
        self.state_changes: List[Dict[str, Any]] = []  # Audit trail for quarantine/re-enable
        
        # Configurable thresholds
        self.min_acceptable_win_rate = 0.40
        self.min_trades_for_metrics = 3
        self.consecutive_loss_limit = 2
        self.lookback_window = 20  # Only consider last N trades for moving metrics
    
    def record_trade(self, outcome: TradeOutcome) -> Dict[str, Any]:
        """Record a completed trade and update metrics."""
        self.trade_history.append(outcome)
        
        # Generate strategy key
        strategy_key = f"{outcome.template_id}_{outcome.regime}_{outcome.time_of_day}"
        
        # Create or retrieve metrics
        if strategy_key not in self.metrics:
            self.metrics[strategy_key] = ReliabilityMetrics(
                strategy_key=strategy_key,
                template_id=outcome.template_id,
                regime=outcome.regime,
                time_of_day=outcome.time_of_day,
            )
        
        metrics = self.metrics[strategy_key]
        metrics.update_from_trade(outcome)
        
        # Check quarantine conditions
        should_quarantine, quarantine_reason = metrics.should_quarantine(self.min_acceptable_win_rate)
        if should_quarantine and metrics.state == StrategyState.ACTIVE:
            metrics.state = StrategyState.QUARANTINED
            metrics.state_change_reason = quarantine_reason
            self.state_changes.append({
                "timestamp": datetime.utcnow().isoformat(),
                "strategy_key": strategy_key,
                "action": "QUARANTINE",
                "reason": quarantine_reason,
                "metrics": {
                    "trades": metrics.trades_count,
                    "win_rate": metrics.win_rate,
                    "expectancy": float(metrics.expectancy),
                    "consecutive_losses": metrics.consecutive_losses,
                }
            })
            if self.logger:
                self.logger.info(f"Strategy {strategy_key} QUARANTINED: {quarantine_reason}")
        
        # Check re-enable conditions
        if metrics.state == StrategyState.QUARANTINED:
            should_enable, enable_reason = metrics.should_re_enable()
            if should_enable:
                metrics.state = StrategyState.ACTIVE
                metrics.state_change_reason = enable_reason
                metrics.consecutive_wins = 0
                metrics.consecutive_losses = 0
                self.state_changes.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "strategy_key": strategy_key,
                    "action": "RE_ENABLE",
                    "reason": enable_reason,
                    "metrics": {
                        "trades": metrics.trades_count,
                        "win_rate": metrics.win_rate,
                        "expectancy": float(metrics.expectancy),
                    }
                })
                if self.logger:
                    self.logger.info(f"Strategy {strategy_key} RE-ENABLED: {enable_reason}")
        
        # Compute throttle level
        throttle_level = metrics.compute_throttle_level(self.min_acceptable_win_rate)
        if throttle_level != metrics.throttle_level:
            old_level = metrics.throttle_level
            metrics.throttle_level = throttle_level
            if throttle_level > 0:
                metrics.throttle_reason = f"WIN_RATE_{metrics.win_rate:.1%}"
                if self.logger:
                    self.logger.warn(f"Strategy {strategy_key} throttle level {old_level} → {throttle_level}")
        
        return {
            "trade_id": outcome.trade_id,
            "strategy_key": strategy_key,
            "metrics": self._serialize_metrics(metrics),
            "action": "UPDATED",
        }
    
    def get_strategy_state(self, template_id: str, regime: str, time_of_day: str) -> Tuple[StrategyState, int]:
        """Get current state and throttle level for a strategy."""
        strategy_key = f"{template_id}_{regime}_{time_of_day}"
        if strategy_key not in self.metrics:
            return StrategyState.ACTIVE, 0
        
        metrics = self.metrics[strategy_key]
        return metrics.state, metrics.throttle_level
    
    def get_euc_cost_modifier(self, template_id: str, regime: str, time_of_day: str) -> float:
        """
        Get EUC cost modifier for decision engine based on strategy state.
        
        ACTIVE (throttle 0): 1.0 (no modifier)
        THROTTLED mild (throttle 1): 1.2 (20% friction)
        THROTTLED heavy (throttle 2): 1.5 (50% friction)
        QUARANTINED: 10.0 (block)
        """
        state, throttle_level = self.get_strategy_state(template_id, regime, time_of_day)
        
        if state == StrategyState.QUARANTINED:
            return 10.0  # Block strategy
        elif state == StrategyState.THROTTLED or throttle_level > 0:
            if throttle_level == 1:
                return 1.2
            elif throttle_level == 2:
                return 1.5
            else:
                return 1.0
        else:
            return 1.0
    
    def get_all_metrics(self) -> Dict[str, ReliabilityMetrics]:
        """Return all strategy metrics."""
        return self.metrics
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Summary of all strategies: state, win rate, expectancy."""
        summary = {}
        for key, metrics in self.metrics.items():
            summary[key] = {
                "state": metrics.state.name,
                "trades": metrics.trades_count,
                "win_rate": f"{metrics.win_rate:.1%}",
                "expectancy": f"${float(metrics.expectancy):.2f}",
                "sharpe": f"{metrics.sharpe_ratio:.2f}",
                "throttle_level": metrics.throttle_level,
            }
        return summary
    
    def get_state_changes(self, since: datetime | None = None) -> List[Dict[str, Any]]:
        """Get audit trail of quarantine/re-enable events."""
        if since is None:
            return self.state_changes
        
        return [
            event for event in self.state_changes
            if datetime.fromisoformat(event["timestamp"]) >= since
        ]
    
    def _serialize_metrics(self, metrics: ReliabilityMetrics) -> Dict[str, Any]:
        """Serialize metrics for JSON logging."""
        return {
            "strategy_key": metrics.strategy_key,
            "template_id": metrics.template_id,
            "regime": metrics.regime,
            "time_of_day": metrics.time_of_day,
            "trades_count": metrics.trades_count,
            "wins": metrics.wins,
            "losses": metrics.losses,
            "win_rate": f"{metrics.win_rate:.1%}",
            "expectancy": f"${float(metrics.expectancy):.2f}",
            "sharpe_ratio": f"{metrics.sharpe_ratio:.2f}",
            "max_drawdown": f"${float(metrics.max_drawdown):.2f}",
            "state": metrics.state.name,
            "throttle_level": metrics.throttle_level,
        }
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export full learning state for persistence."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                k: self._serialize_metrics(v)
                for k, v in self.metrics.items()
            },
            "state_changes": self.state_changes,
            "config": {
                "min_acceptable_win_rate": self.min_acceptable_win_rate,
                "min_trades_for_metrics": self.min_trades_for_metrics,
                "consecutive_loss_limit": self.consecutive_loss_limit,
                "lookback_window": self.lookback_window,
            }
        }
    
    def load_from_dict(self, state: Dict[str, Any]) -> None:
        """Load learning state from persistence (e.g., JSON file)."""
        # Note: This is a placeholder; full reconstruction would deserialize TradeOutcome history
        # For now, just restore metrics and state_changes
        if "metrics" in state:
            for key, m in state["metrics"].items():
                # Reconstruct ReliabilityMetrics from dict
                metrics = ReliabilityMetrics(
                    strategy_key=key,
                    template_id=m["template_id"],
                    regime=m["regime"],
                    time_of_day=m["time_of_day"],
                    trades_count=m.get("trades_count", 0),
                    wins=m.get("wins", 0),
                    losses=m.get("losses", 0),
                )
                self.metrics[key] = metrics
        
        if "state_changes" in state:
            self.state_changes = state["state_changes"]
        
        if "config" in state:
            cfg = state["config"]
            self.min_acceptable_win_rate = cfg.get("min_acceptable_win_rate", 0.40)
            self.min_trades_for_metrics = cfg.get("min_trades_for_metrics", 3)
            self.consecutive_loss_limit = cfg.get("consecutive_loss_limit", 2)
            self.lookback_window = cfg.get("lookback_window", 20)
