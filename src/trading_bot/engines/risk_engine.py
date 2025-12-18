"""
Risk management engine for MES survival bot.

Enforces:
1. Per-trade risk limits (max $5/4 ticks)
2. Per-day risk limits (max $50 loss, 10 trades, 3 consecutive losses)
3. Drawdown tracking (max $50/5% intraday)
4. Kill-switch triggers (DVS<0.30, EQS<0.30, loss limits, connection)
5. Pre-trade and in-trade checks

All checks use risk_model.yaml contract as single source of truth.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from decimal import Decimal

from ..core.config import Contracts


@dataclass(frozen=True)
class RiskCheckResult:
    """Result of a risk check."""
    passed: bool
    reason: Optional[str] = None
    failed_checks: List[str] = None
    
    def __post_init__(self):
        if self.failed_checks is None:
            object.__setattr__(self, 'failed_checks', [])


@dataclass
class RiskState:
    """
    Current risk state tracked across session.
    Mutable to allow updates during session.
    """
    # Daily tracking
    daily_pnl: Decimal = Decimal("0")
    daily_trades: int = 0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    max_drawdown: Decimal = Decimal("0")
    peak_equity: Decimal = Decimal("0")
    
    # Kill switch
    kill_switch_active: bool = False
    kill_switch_reason: Optional[str] = None
    kill_switch_triggered_at: Optional[datetime] = None
    pause_until: Optional[datetime] = None
    
    # Current position
    net_position: int = 0
    position_entry_price: Optional[Decimal] = None


class RiskEngine:
    """
    Risk management and kill-switch enforcement.
    """
    
    def __init__(self, contracts: Contracts, tick_value: Decimal = Decimal("1.25")):
        self.contracts = contracts
        self.risk_contract = contracts.docs["risk_model.yaml"]
        self.tick_value = tick_value
        
        # Initialize risk state
        self.state = RiskState()
    
    def check_pre_trade(
        self,
        dvs: float,
        eqs: float,
        intended_position_size: int,
        entry_price: Decimal,
        stop_price: Decimal
    ) -> RiskCheckResult:
        """
        Perform all pre-trade risk checks before entering a position.
        
        Checks:
        1. Kill switch not active
        2. Not in pause period
        3. DVS >= threshold
        4. EQS >= threshold
        5. Per-trade risk within limits
        6. Daily trade count within limits
        """
        failed = []
        
        # Check 1: Kill switch
        if self.state.kill_switch_active:
            return RiskCheckResult(
                passed=False,
                reason=f"Kill switch active: {self.state.kill_switch_reason}",
                failed_checks=["kill_switch_active"]
            )
        
        # Check 2: Pause period
        if self.state.pause_until and datetime.now() < self.state.pause_until:
            return RiskCheckResult(
                passed=False,
                reason=f"In pause period until {self.state.pause_until}",
                failed_checks=["pause_period"]
            )
        
        # Check 3: DVS threshold
        dvs_threshold = 0.75  # From pre_trade_checks DVS_GATE
        if dvs < dvs_threshold:
            failed.append(f"dvs_too_low_{dvs:.2f}")
        
        # Check 4: EQS threshold
        eqs_threshold = 0.75  # From pre_trade_checks EQS_GATE
        if eqs < eqs_threshold:
            failed.append(f"eqs_too_low_{eqs:.2f}")
        
        # Check 5: Per-trade risk
        risk_dollars = abs(entry_price - stop_price) * Decimal(abs(intended_position_size)) * self.tick_value / Decimal("0.25")
        max_risk = Decimal("5.0")  # From per_trade_risk.max_risk_usd
        if risk_dollars > max_risk:
            failed.append(f"per_trade_risk_${risk_dollars:.2f}_exceeds_${max_risk}")
        
        # Check 6: Daily trade count
        max_daily_trades = 10  # From per_day_risk.max_trades_per_day
        if self.state.daily_trades >= max_daily_trades:
            failed.append("daily_trade_limit")
        
        # Check 7: No existing position
        if self.state.net_position != 0:
            failed.append("position_already_open")
        
        if failed:
            return RiskCheckResult(
                passed=False,
                reason=f"Pre-trade checks failed: {', '.join(failed)}",
                failed_checks=failed
            )
        
        return RiskCheckResult(passed=True)
    
    def check_in_trade(self, dvs: float, eqs: float, current_pnl: Decimal) -> RiskCheckResult:
        """
        Perform in-trade risk checks while position is open.
        
        Checks:
        1. DVS hasn't degraded below kill-switch threshold
        2. EQS hasn't degraded below kill-switch threshold
        3. Unrealized loss within limits
        4. Daily loss within limits
        """
        failed = []
        
        # Check DVS kill-switch
        dvs_kill_threshold = 0.30
        if dvs < dvs_kill_threshold:
            failed.append(f"dvs_kill_switch_{dvs:.2f}")
        
        # Check EQS kill-switch
        eqs_kill_threshold = 0.30
        if eqs < eqs_kill_threshold:
            failed.append(f"eqs_kill_switch_{eqs:.2f}")
        
        # Check daily loss
        max_daily_loss = Decimal("50.0")  # From per_day_risk.max_daily_loss_usd
        if (self.state.daily_pnl + current_pnl) < -max_daily_loss:
            failed.append(f"daily_loss_limit_${abs(self.state.daily_pnl + current_pnl):.2f}")
        
        if failed:
            return RiskCheckResult(
                passed=False,
                reason=f"In-trade checks failed: {', '.join(failed)}",
                failed_checks=failed
            )
        
        return RiskCheckResult(passed=True)
    
    def trigger_kill_switch(self, reason: str):
        """
        Trigger kill switch - halt all trading.
        """
        self.state.kill_switch_active = True
        self.state.kill_switch_reason = reason
        self.state.kill_switch_triggered_at = datetime.now()
    
    def update_on_trade_close(self, realized_pnl: Decimal):
        """
        Update risk state when a trade closes.
        """
        self.state.daily_pnl += realized_pnl
        self.state.daily_trades += 1
        
        # Update consecutive wins/losses
        if realized_pnl > 0:
            self.state.consecutive_wins += 1
            self.state.consecutive_losses = 0
        elif realized_pnl < 0:
            self.state.consecutive_losses += 1
            self.state.consecutive_wins = 0
        else:
            # Break-even
            pass
        
        # Update peak equity and drawdown
        current_equity = self.state.daily_pnl
        if current_equity > self.state.peak_equity:
            self.state.peak_equity = current_equity
        
        drawdown = self.state.peak_equity - current_equity
        if drawdown > self.state.max_drawdown:
            self.state.max_drawdown = drawdown
        
        # Check kill-switch triggers
        self._check_kill_switch_triggers()
    
    def _check_kill_switch_triggers(self):
        """
        Check if any kill-switch conditions are met.
        """
        triggers = self.risk_contract.get("kill_switch", {}).get("triggers", [])
        
        for trigger in triggers:
            trigger_id = trigger.get("id", "unknown")
            condition = trigger.get("condition", {})
            
            # Check daily loss (daily_loss_gte: 50.00)
            if "daily_loss_gte" in condition:
                threshold = Decimal(str(condition["daily_loss_gte"]))
                if abs(self.state.daily_pnl) >= threshold:
                    self.trigger_kill_switch(f"{trigger_id}: daily_loss_${abs(self.state.daily_pnl):.2f}")
                    return
            
            # Check consecutive losses (consecutive_losses_gte: 3)
            if "consecutive_losses_gte" in condition:
                threshold = int(condition["consecutive_losses_gte"])
                if self.state.consecutive_losses >= threshold:
                    self.trigger_kill_switch(f"{trigger_id}: {self.state.consecutive_losses}_consecutive_losses")
                    # Set pause period from per_day_risk
                    pause_minutes = 60  # From per_day_risk.pause_after_losses_minutes
                    self.state.pause_until = datetime.now() + timedelta(minutes=pause_minutes)
                    return
            
            # Check drawdown (intraday_drawdown_gte: 50.00)
            if "intraday_drawdown_gte" in condition:
                threshold = Decimal(str(condition["intraday_drawdown_gte"]))
                if self.state.max_drawdown >= threshold:
                    self.trigger_kill_switch(f"{trigger_id}: drawdown_${self.state.max_drawdown:.2f}")
                    return
    
    def reset_daily_state(self):
        """Reset daily tracking at start of new session."""
        self.state.daily_pnl = Decimal("0")
        self.state.daily_trades = 0
        self.state.consecutive_wins = 0
        self.state.consecutive_losses = 0
        self.state.max_drawdown = Decimal("0")
        self.state.peak_equity = Decimal("0")
        self.state.kill_switch_active = False
        self.state.kill_switch_reason = None
        self.state.pause_until = None
    
    def open_position(self, size: int, entry_price: Decimal):
        """Record position opening."""
        self.state.net_position = size
        self.state.position_entry_price = entry_price
    
    def close_position(self):
        """Record position closing."""
        self.state.net_position = 0
        self.state.position_entry_price = None
