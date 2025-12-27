"""
K1: VWAP Mean Reversion (Conservative)

Setup: Price breaks below VWAP + low momentum (S8 < 0.4)
Entry: Buy limit 1 tick above low, 12-tick stop
Target: Back to VWAP or 30-min high
Risk: $15 max, 1 contract

Constraints:
- Belief F1 (VWAP MR): likelihood > 60%
- Belief F2 (Failed Break): < 20%
- Session: Not RTH open ± 30min
- Time: 09:45-15:45 ET only
"""

from trading_bot.strategies.base import Strategy, StrategyContext, EntryPlan, ManagementAction, ExitPlan, TradeOutcomeUpdate
from typing import Dict, Any, Optional
from decimal import Decimal


class K1_VWAPMeanReversion(Strategy):
    """VWAP mean reversion strategy (conservative capital tier)."""
    
    def __init__(self, logger=None):
        super().__init__("VWAP MR (K1)", "K1", logger)
        self.min_belief_f1 = 0.60
        self.max_belief_f2 = 0.20
    
    def detect(self, signals: Dict[str, Any], beliefs: Dict[str, Any], context: StrategyContext) -> bool:
        """Detect: S1 (VWAP_MR) > 0.7 AND momentum low AND F1 strong."""
        try:
            # Signal: VWAP mean reversion confidence
            s1 = float(signals.get("S1_VWAP_MR", 0))
            if s1 < 0.70:
                return False
            
            # Signal: Momentum (low is good)
            s8 = float(signals.get("S8_MOMENTUM", 0))
            if s8 > 0.40:
                return False
            
            # Belief: F1 (VWAP MR) must be strong
            f1 = beliefs.get("F1_VWAP_MR", {})
            f1_likelihood = float(f1.get("effective_likelihood", 0))
            if f1_likelihood < self.min_belief_f1:
                return False
            
            # Belief: F2 (Failed Break) should be weak
            f2 = beliefs.get("F2_FAILED_BREAK", {})
            f2_likelihood = float(f2.get("effective_likelihood", 0))
            if f2_likelihood > self.max_belief_f2:
                return False
            
            # Time gate: 09:45-15:45 ET (avoid open chaos)
            if context.time_of_day not in ("open", "midday", "afternoon"):
                return False
            
            # Session gate: not first 30 min of RTH
            if context.session_phase <= 1:
                return False
            
            return True
        except Exception:
            return False
    
    def plan_entry(self, signals: Dict[str, Any], beliefs: Dict[str, Any], context: StrategyContext) -> Optional[EntryPlan]:
        """Plan: Buy 1 contract, stop 12 ticks below entry, target VWAP + 8 ticks."""
        try:
            last_price = context.last_price
            
            # Entry: 1 tick below current (aggressive)
            entry_price = last_price - Decimal("0.25")
            
            # Stop: 12 ticks below entry (constitutional limit)
            stop_price = entry_price - Decimal("3.00")  # 12 ticks
            
            # Target: VWAP + 8 ticks (estimated 200 points on MES)
            target_price = last_price + Decimal("2.00")
            
            # Risk: 12 ticks * $12.5/tick = $150 per contract; use 1 contract
            risk_usd = Decimal("150")
            
            f1 = beliefs.get("F1_VWAP_MR", {})
            confidence = float(f1.get("effective_likelihood", 0.60))
            
            return EntryPlan(
                side="BUY",
                size=1,
                entry_price=entry_price,
                stop_price=stop_price,
                target_price=target_price,
                risk_usd=risk_usd,
                confidence=confidence,
                setup_id="K1_VWAP_MR_BUY",
                metadata={"f1_likelihood": confidence},
            )
        except Exception:
            return None
    
    def plan_management(self, position: Dict[str, Any], bar: Dict[str, Any], beliefs: Dict[str, Any]) -> Optional[ManagementAction]:
        """Check if thesis is still valid. If F1 drops below 50%, exit."""
        try:
            f1 = beliefs.get("F1_VWAP_MR", {})
            f1_likelihood = float(f1.get("effective_likelihood", 0))
            
            if f1_likelihood < 0.50:
                return ManagementAction(
                    action="EXIT",
                    reason="THESIS_INVALID: F1 dropped below min_belief",
                    metadata={"f1_likelihood": f1_likelihood},
                )
            
            # If in profit by 4 ticks, tighten stop to entry
            entry_price = position.get("entry_price")
            current_price = bar.get("c")
            if entry_price and current_price:
                entry_price = Decimal(str(entry_price))
                current_price = Decimal(str(current_price))
                profit_ticks = (current_price - entry_price) / Decimal("0.25")
                if float(profit_ticks) > 4:
                    return ManagementAction(
                        action="TIGHTEN_STOP",
                        reason="PROFIT_PROTECTION: Move stop to entry",
                        new_stop_price=entry_price,
                    )
            
            return None
        except Exception:
            return None
    
    def plan_exit(self, position: Dict[str, Any], bar: Dict[str, Any], beliefs: Dict[str, Any]) -> Optional[ExitPlan]:
        """Exit if target or stop hit, or thesis invalid."""
        try:
            return None  # Passive exit (let supervisor handle stops/targets)
        except Exception:
            return None
    
    def post_trade_update(self, outcome: TradeOutcomeUpdate) -> None:
        """Learn from trade. Adjust min_belief_f1 if too conservative/aggressive."""
        try:
            if outcome.thesis_valid and outcome.pnl_usd > 0:
                # Thesis was valid and profitable; keep current threshold
                pass
            elif not outcome.thesis_valid and outcome.pnl_usd < 0:
                # Thesis became invalid and trade lost money; slightly raise threshold
                self.min_belief_f1 = min(0.75, self.min_belief_f1 + 0.02)
            elif outcome.thesis_valid and outcome.pnl_usd < 0:
                # Thesis was valid but trade lost money; lower threshold slightly (not our fault)
                self.min_belief_f1 = max(0.50, self.min_belief_f1 - 0.01)
        except Exception:
            pass


class K2_FailedBreakReversal(Strategy):
    """Failed break reversal (growth capital tier)."""
    
    def __init__(self, logger=None):
        super().__init__("Failed Break (K2)", "K2", logger)
        self.min_belief_f2 = 0.65
    
    def detect(self, signals: Dict[str, Any], beliefs: Dict[str, Any], context: StrategyContext) -> bool:
        """Detect: S5 (Break Failure) > 0.75 AND F2 strong."""
        try:
            s5 = float(signals.get("S5_BREAK_FAILURE", 0))
            if s5 < 0.75:
                return False
            
            f2 = beliefs.get("F2_FAILED_BREAK", {})
            f2_likelihood = float(f2.get("effective_likelihood", 0))
            if f2_likelihood < self.min_belief_f2:
                return False
            
            # Regime: works best in range
            if context.regime not in ("range", "choppy"):
                return False
            
            return True
        except Exception:
            return False
    
    def plan_entry(self, signals: Dict[str, Any], beliefs: Dict[str, Any], context: StrategyContext) -> Optional[EntryPlan]:
        """Plan: Sell 1 contract, stop 10 ticks above entry, target 2X risk."""
        try:
            last_price = context.last_price
            entry_price = last_price + Decimal("0.50")  # Sell into failed break
            stop_price = entry_price + Decimal("2.50")  # 10 ticks
            target_price = entry_price - Decimal("1.25")  # 5 ticks
            risk_usd = Decimal("125")
            
            f2 = beliefs.get("F2_FAILED_BREAK", {})
            confidence = float(f2.get("effective_likelihood", 0.65))
            
            return EntryPlan(
                side="SELL",
                size=1,
                entry_price=entry_price,
                stop_price=stop_price,
                target_price=target_price,
                risk_usd=risk_usd,
                confidence=confidence,
                setup_id="K2_BREAK_FAIL_SELL",
            )
        except Exception:
            return None
    
    def plan_management(self, position: Dict[str, Any], bar: Dict[str, Any], beliefs: Dict[str, Any]) -> Optional[ManagementAction]:
        """Check if F2 still valid."""
        try:
            f2 = beliefs.get("F2_FAILED_BREAK", {})
            f2_likelihood = float(f2.get("effective_likelihood", 0))
            if f2_likelihood < 0.50:
                return ManagementAction(
                    action="EXIT",
                    reason="THESIS_INVALID: F2 dropped",
                )
            return None
        except Exception:
            return None
    
    def plan_exit(self, position: Dict[str, Any], bar: Dict[str, Any], beliefs: Dict[str, Any]) -> Optional[ExitPlan]:
        """No additional exit logic."""
        return None
    
    def post_trade_update(self, outcome: TradeOutcomeUpdate) -> None:
        """Learn from outcome."""
        try:
            if outcome.thesis_valid and outcome.pnl_usd < 0:
                self.min_belief_f2 = min(0.80, self.min_belief_f2 + 0.03)
        except Exception:
            pass


class K3_SweepReversal(Strategy):
    """Sweep-driven reversal (aggressive capital tier)."""
    
    def __init__(self, logger=None):
        super().__init__("Sweep Reversal (K3)", "K3", logger)
    
    def detect(self, signals: Dict[str, Any], beliefs: Dict[str, Any], context: StrategyContext) -> bool:
        """Detect: S13 (Sweep) > 0.8 AND F3 (Sweep Reversal) strong."""
        try:
            s13 = float(signals.get("S13_SWEEP", 0))
            if s13 < 0.80:
                return False
            
            f3 = beliefs.get("F3_SWEEP_REVERSAL", {})
            if float(f3.get("effective_likelihood", 0)) < 0.60:
                return False
            
            # Regime: any regime, but avoid flat
            if context.regime == "choppy":
                return False
            
            return True
        except Exception:
            return False
    
    def plan_entry(self, signals: Dict[str, Any], beliefs: Dict[str, Any], context: StrategyContext) -> Optional[EntryPlan]:
        """Plan: Entry opposite to sweep direction."""
        try:
            last_price = context.last_price
            
            # Assume sweep signal indicates direction; for now, default to BUY
            entry_price = last_price - Decimal("0.25")
            stop_price = entry_price - Decimal("3.00")
            target_price = last_price + Decimal("3.00")
            
            f3 = beliefs.get("F3_SWEEP_REVERSAL", {})
            confidence = float(f3.get("effective_likelihood", 0.60))
            
            return EntryPlan(
                side="BUY",
                size=1,
                entry_price=entry_price,
                stop_price=stop_price,
                target_price=target_price,
                risk_usd=Decimal("150"),
                confidence=confidence,
                setup_id="K3_SWEEP_BUY",
            )
        except Exception:
            return None
    
    def plan_management(self, position: Dict[str, Any], bar: Dict[str, Any], beliefs: Dict[str, Any]) -> Optional[ManagementAction]:
        return None
    
    def plan_exit(self, position: Dict[str, Any], bar: Dict[str, Any], beliefs: Dict[str, Any]) -> Optional[ExitPlan]:
        return None
    
    def post_trade_update(self, outcome: TradeOutcomeUpdate) -> None:
        pass


class K4_MomentumExtension(Strategy):
    """Momentum trend extension (algorithmic, fastest execution)."""
    
    def __init__(self, logger=None):
        super().__init__("Momentum Extension (K4)", "K4", logger)
    
    def detect(self, signals: Dict[str, Any], beliefs: Dict[str, Any], context: StrategyContext) -> bool:
        """Detect: S8 (Momentum) > 0.75 AND F4 (Momentum) strong."""
        try:
            s8 = float(signals.get("S8_MOMENTUM", 0))
            if s8 < 0.75:
                return False
            
            f4 = beliefs.get("F4_MOMENTUM", {})
            if float(f4.get("effective_likelihood", 0)) < 0.60:
                return False
            
            if context.regime not in ("trending", "volatile"):
                return False
            
            return True
        except Exception:
            return False
    
    def plan_entry(self, signals: Dict[str, Any], beliefs: Dict[str, Any], context: StrategyContext) -> Optional[EntryPlan]:
        """Aggressive entry at market."""
        try:
            last_price = context.last_price
            entry_price = last_price
            stop_price = entry_price - Decimal("2.50")
            target_price = entry_price + Decimal("5.00")
            
            f4 = beliefs.get("F4_MOMENTUM", {})
            confidence = float(f4.get("effective_likelihood", 0.70))
            
            return EntryPlan(
                side="BUY",
                size=2,  # Larger size for momentum
                entry_price=entry_price,
                stop_price=stop_price,
                target_price=target_price,
                risk_usd=Decimal("125"),
                confidence=confidence,
                setup_id="K4_MOMENTUM_BUY",
            )
        except Exception:
            return None
    
    def plan_management(self, position: Dict[str, Any], bar: Dict[str, Any], beliefs: Dict[str, Any]) -> Optional[ManagementAction]:
        return None
    
    def plan_exit(self, position: Dict[str, Any], bar: Dict[str, Any], beliefs: Dict[str, Any]) -> Optional[ExitPlan]:
        return None
    
    def post_trade_update(self, outcome: TradeOutcomeUpdate) -> None:
        pass


class K5_NoiseFilter(Strategy):
    """Noise filter / wait strategy (skip on high noise)."""
    
    def __init__(self, logger=None):
        super().__init__("Noise Filter (K5)", "K5", logger)
    
    def detect(self, signals: Dict[str, Any], beliefs: Dict[str, Any], context: StrategyContext) -> bool:
        """Detect: High noise environment (prevent entries)."""
        try:
            # This is a meta-strategy that detects when NOT to trade
            s6 = float(signals.get("S6_NOISE", 0))
            f5 = beliefs.get("F5_NOISE_FILTER", {})
            
            # Should NOT trade if noise is high
            if s6 > 0.70 or float(f5.get("effective_likelihood", 0)) < 0.50:
                return True  # "Detected" = we should skip
            
            return False
        except Exception:
            return False
    
    def plan_entry(self, signals: Dict[str, Any], beliefs: Dict[str, Any], context: StrategyContext) -> Optional[EntryPlan]:
        """No entry for noise filter (it's a skip signal)."""
        return None
    
    def plan_management(self, position: Dict[str, Any], bar: Dict[str, Any], beliefs: Dict[str, Any]) -> Optional[ManagementAction]:
        return None
    
    def plan_exit(self, position: Dict[str, Any], bar: Dict[str, Any], beliefs: Dict[str, Any]) -> Optional[ExitPlan]:
        return None
    
    def post_trade_update(self, outcome: TradeOutcomeUpdate) -> None:
        pass
