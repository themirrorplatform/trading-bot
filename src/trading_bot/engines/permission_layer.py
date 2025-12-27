"""
Permission Layer - Generates trade permission from bias/strategy gates.

This sits between Believe and Act, controlling whether trades are allowed.
"""
from __future__ import annotations

from typing import Dict, Any, List, Literal

from trading_bot.core.bias_strategy_types import BiasState, StrategyState, Permission


class PermissionLayer:
    """Computes Permission from BiasState + StrategyState + BeliefState."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        # Thresholds
        self.min_bias_strength = self.config.get("min_bias_strength", 0.4)
        self.min_bias_confidence = self.config.get("min_bias_confidence", 0.6)
        self.min_strategy_probability = self.config.get("min_strategy_probability", 0.4)
        self.max_conflict_severity = self.config.get("max_conflict_severity", 0.5)
    
    def compute(self, bias_state: BiasState, strategy_state: StrategyState, 
                belief_state: Dict[str, Any], context: Dict[str, Any]) -> Permission:
        """Generate Permission for this cycle."""
        
        # Gate 1: Regime Suitability
        regime_ok, regime_reason = self._check_regime_gate(bias_state)
        if not regime_ok:
            return Permission(
                allow_trade=False,
                stand_down_reason=f"REGIME_UNSUITABLE: {regime_reason}"
            )
        
        # Gate 2: Bias Quality
        strong_biases = [b for b in bias_state.active 
                        if b["strength"] >= self.min_bias_strength 
                        and b["confidence"] >= self.min_bias_confidence]
        
        if not strong_biases:
            return Permission(
                allow_trade=False,
                stand_down_reason="NO_STRONG_BIAS"
            )
        
        # Gate 3: Bias Conflicts
        severe_conflicts = [c for c in bias_state.conflicts 
                           if c["severity"] >= self.max_conflict_severity]
        
        if severe_conflicts:
            return Permission(
                allow_trade=False,
                stand_down_reason=f"BIAS_CONFLICT: {severe_conflicts[0]['a']} vs {severe_conflicts[0]['b']}"
            )
        
        # Gate 4: Strategy Detection
        dominant_strategies = [s for s in strategy_state.dominance 
                             if s["dominance_score"] >= self.min_strategy_probability]
        
        if not dominant_strategies:
            return Permission(
                allow_trade=False,
                stand_down_reason="NO_DOMINANT_STRATEGY"
            )
        
        # Gate 5: Strategy Traps
        trapped_strategies = [s for s in strategy_state.traps if s["trap_score"] > 0.7]
        if len(trapped_strategies) > len(dominant_strategies):
            return Permission(
                allow_trade=False,
                stand_down_reason="STRATEGY_TRAP_DOMINANT"
            )
        
        # Determine allowed directions
        allowed_directions = self._determine_directions(bias_state, strategy_state)
        
        # Determine allowed playbooks
        allowed_playbooks = [s["strategy_id"] for s in dominant_strategies]
        
        # Risk scaling based on confidence
        max_risk = self._compute_risk_units(bias_state, strategy_state)
        
        # Required confirmations
        required_confirmation = self._determine_required_signals(bias_state, strategy_state)
        
        return Permission(
            allow_trade=True,
            allowed_directions=allowed_directions,
            allowed_playbooks=allowed_playbooks,
            max_risk_units=max_risk,
            required_confirmation=required_confirmation
        )
    
    def _check_regime_gate(self, bias_state: BiasState) -> tuple[bool, str]:
        """Check if regime allows trading."""
        regime = bias_state.regime
        
        # Dead market - no trade
        if regime.get("vol_regime") == "LOW" and regime.get("liquidity_regime") == "THIN":
            return False, "DEAD_MARKET"
        
        # Liquidity vacuum - no trade
        if regime.get("liquidity_regime") == "THIN" and regime.get("vol_regime") == "HIGH":
            return False, "LIQUIDITY_VACUUM"
        
        # Mixed regime with no clear bias - risky
        if regime.get("trend_regime") == "MIXED":
            # Allow only if strong biases exist
            strong_count = len([b for b in bias_state.active if b["strength"] > 0.6])
            if strong_count < 2:
                return False, "MIXED_REGIME_WEAK_BIAS"
        
        return True, ""
    
    def _determine_directions(self, bias_state: BiasState, strategy_state: StrategyState) -> List[Literal["LONG", "SHORT"]]:
        """Determine allowed trade directions."""
        # TODO: Implement directional bias from signals/biases
        # For now, allow both if regime is clear
        regime = bias_state.regime
        
        if regime.get("trend_regime") == "TRENDING":
            # Check if trend is up or down from momentum bias
            trend_biases = [b for b in bias_state.active if "TREND" in b["bias_id"]]
            if trend_biases:
                # Would need directional info from signals
                return ["LONG", "SHORT"]  # Placeholder
        
        return ["LONG", "SHORT"]  # Default: allow both
    
    def _compute_risk_units(self, bias_state: BiasState, strategy_state: StrategyState) -> float:
        """Compute max risk units based on confidence."""
        if not bias_state.active or not strategy_state.dominance:
            return 0.0
        
        # Average bias confidence
        avg_bias_conf = sum(b["confidence"] for b in bias_state.active) / len(bias_state.active)
        
        # Top strategy dominance
        top_strategy_dom = strategy_state.dominance[0]["dominance_score"] if strategy_state.dominance else 0.0
        
        # Risk scaling: 1.0 at full confidence, 0.5 at minimum
        combined_confidence = (avg_bias_conf * 0.6) + (top_strategy_dom * 0.4)
        
        return max(0.5, min(1.0, combined_confidence))
    
    def _determine_required_signals(self, bias_state: BiasState, strategy_state: StrategyState) -> List[str]:
        """Determine which signals must confirm before entry."""
        required = []
        
        # If reversion bias active, require value signal
        reversion_active = any("REVERSION" in b["bias_id"] for b in bias_state.active)
        if reversion_active:
            required.append("F4")  # Value factor
        
        # If trend bias active, require momentum
        trend_active = any("TREND" in b["bias_id"] for b in bias_state.active)
        if trend_active:
            required.append("F5")  # Momentum factor
        
        # If breakout strategy dominant, require volume confirmation
        breakout_dominant = any("BREAKOUT" in s["strategy_id"] for s in strategy_state.dominance)
        if breakout_dominant:
            required.append("T5")  # Volatility/volume proxy
        
        return required
