"""
Threshold Modifiers - Context-aware adjustments to decision thresholds.

These adjust θ (decision threshold) based on:
- Time of day
- Day of week  
- Market regime (volatility, liquidity)
- Strategy conflicts

Core principle: Don't block trades, make them conditional.
Higher θ = harder to take trade, but still possible if edge is strong enough.
"""
from typing import Dict, Any
from datetime import datetime, time
from decimal import Decimal


class ThresholdModifiers:
    """Computes context-based adjustments to decision threshold."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Time-based modifiers
        self.time_modifiers = self.config.get("time_modifiers", {
            "open_30min": 0.0,          # First 30 min: neutral
            "morning_trend": -0.05,      # 10:00-11:30: slightly easier (trend continuation)
            "lunch": 0.10,               # 11:30-13:00: harder (chop risk)
            "afternoon": 0.0,            # 13:00-15:00: neutral
            "power_hour": -0.05,         # 15:00-15:45: slightly easier (momentum)
            "close_15min": 0.15          # 15:45-16:00: much harder (position squaring)
        })
        
        # Day-of-week modifiers
        self.day_modifiers = self.config.get("day_modifiers", {
            "monday": 0.05,              # Monday: slightly harder (weekend gap risk)
            "tuesday": 0.0,
            "wednesday": 0.0,
            "thursday": 0.0,
            "friday_pre_close": 0.05,    # Friday before 14:00: slightly harder
            "friday_close": 0.10         # Friday after 14:00: harder (weekend risk)
        })
        
        # Regime modifiers
        self.regime_modifiers = self.config.get("regime_modifiers", {
            "high_volatility": 0.10,     # ATR > 1.5x avg: harder
            "low_volatility": -0.05,     # ATR < 0.7x avg: slightly easier
            "compression": -0.03,        # Range compression: slightly easier (breakout setup)
            "expansion": 0.05            # Range expansion: harder (whipsaw risk)
        })
        
        # Conflict modifiers
        self.conflict_penalty = self.config.get("conflict_penalty", 0.15)
    
    def compute_effective_threshold(
        self,
        base_threshold: float,
        signals: Dict[str, Any],
        context: Dict[str, Any],
        timestamp: datetime
    ) -> tuple[float, Dict[str, float]]:
        """
        Compute θ_effective = θ_base + Σ(modifiers).
        
        Returns:
            (effective_threshold, active_modifiers_dict)
        """
        active_modifiers = {}
        
        # Time-based modifier
        time_mod = self._get_time_modifier(timestamp)
        if time_mod != 0.0:
            active_modifiers["time_of_day"] = time_mod
        
        # Day-based modifier
        day_mod = self._get_day_modifier(timestamp)
        if day_mod != 0.0:
            active_modifiers["day_of_week"] = day_mod
        
        # Regime-based modifiers
        regime_mods = self._get_regime_modifiers(signals, context)
        active_modifiers.update(regime_mods)
        
        # Strategy conflict penalty
        conflict_mod = self._get_conflict_modifier(signals, context)
        if conflict_mod != 0.0:
            active_modifiers["strategy_conflict"] = conflict_mod
        
        # Sum all modifiers
        total_adjustment = sum(active_modifiers.values())
        effective_threshold = base_threshold + total_adjustment
        
        # Clamp to reasonable bounds [0.3, 0.9]
        effective_threshold = max(0.3, min(0.9, effective_threshold))
        
        return effective_threshold, active_modifiers
    
    def _get_time_modifier(self, timestamp: datetime) -> float:
        """Get time-of-day modifier."""
        t = timestamp.time()
        
        # Market open: 09:30-10:00
        if time(9, 30) <= t < time(10, 0):
            return self.time_modifiers["open_30min"]
        
        # Morning trend: 10:00-11:30
        if time(10, 0) <= t < time(11, 30):
            return self.time_modifiers["morning_trend"]
        
        # Lunch: 11:30-13:00
        if time(11, 30) <= t < time(13, 0):
            return self.time_modifiers["lunch"]
        
        # Afternoon: 13:00-15:00
        if time(13, 0) <= t < time(15, 0):
            return self.time_modifiers["afternoon"]
        
        # Power hour: 15:00-15:45
        if time(15, 0) <= t < time(15, 45):
            return self.time_modifiers["power_hour"]
        
        # Close: 15:45-16:00
        if time(15, 45) <= t < time(16, 0):
            return self.time_modifiers["close_15min"]
        
        return 0.0
    
    def _get_day_modifier(self, timestamp: datetime) -> float:
        """Get day-of-week modifier."""
        weekday = timestamp.weekday()  # 0=Monday, 4=Friday
        t = timestamp.time()
        
        if weekday == 0:  # Monday
            return self.day_modifiers["monday"]
        
        if weekday == 4:  # Friday
            if t < time(14, 0):
                return self.day_modifiers["friday_pre_close"]
            else:
                return self.day_modifiers["friday_close"]
        
        # Tuesday-Thursday
        return 0.0
    
    def _get_regime_modifiers(
        self,
        signals: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """Get regime-based modifiers."""
        modifiers = {}
        
        # Volatility regime
        atr_n = signals.get("atr_14_n")
        if atr_n is not None:
            if atr_n > 1.5:
                modifiers["high_volatility"] = self.regime_modifiers["high_volatility"]
            elif atr_n < 0.7:
                modifiers["low_volatility"] = self.regime_modifiers["low_volatility"]
        
        # Compression/expansion regime
        range_comp = signals.get("range_compression")
        if range_comp is not None:
            if range_comp < 0.5:
                modifiers["compression"] = self.regime_modifiers["compression"]
            elif range_comp > 1.5:
                modifiers["expansion"] = self.regime_modifiers["expansion"]
        
        return modifiers
    
    def _get_conflict_modifier(
        self,
        signals: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """Get strategy conflict penalty."""
        # Check for contradictory signal patterns
        conflicts = self._detect_conflicts(signals, context)
        
        if conflicts:
            return self.conflict_penalty
        
        return 0.0
    
    def _detect_conflicts(
        self,
        signals: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Detect if contradictory strategy patterns are active.
        
        Returns True if conflicts detected.
        """
        # Mean reversion signals
        vwap_z = signals.get("vwap_z", 0.0)
        reversion_active = abs(vwap_z) > 2.0 if vwap_z is not None else False
        
        # Trend continuation signals
        hhll_trend = signals.get("hhll_trend_strength", 0.0)
        trend_active = abs(hhll_trend) > 0.6 if hhll_trend is not None else False
        
        # Conflict: both reversion and trend signals strong
        if reversion_active and trend_active:
            return True
        
        # Breakout signals
        breakout_dist = signals.get("breakout_distance_n", 0.0)
        breakout_active = breakout_dist > 0.5 if breakout_dist is not None else False
        
        # Range compression signals
        range_comp = signals.get("range_compression", 1.0)
        compression_active = range_comp < 0.6 if range_comp is not None else False
        
        # Conflict: breakout signal but still compressed (false breakout risk)
        if breakout_active and compression_active:
            return True
        
        return False
