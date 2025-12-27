"""
Detector primitives - reusable building blocks for biases and strategies.

Each detector is a pure function that consumes:
- bar data
- signal values
- context (recent history, levels, etc.)

Returns: float score [0.0 - 1.0] or boolean detection
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal


class Detector:
    """Base detector interface."""
    
    def __init__(self, name: str):
        self.name = name
    
    def detect(self, bar: Dict[str, Any], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Returns detection score [0.0 - 1.0]."""
        raise NotImplementedError


class BreaksLevel(Detector):
    """Detects price breaking through a key level."""
    
    def __init__(self, level_kind: str, timeframe: str = "5m"):
        super().__init__(f"breaks_level_{level_kind}_{timeframe}")
        self.level_kind = level_kind
        self.timeframe = timeframe
    
    def detect(self, bar: Dict[str, Any], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
        close = bar.get("close", 0)
        level = context.get(f"level_{self.level_kind}")
        if level is None:
            return 0.0
        
        # Check if close crossed level
        prev_close = context.get("prev_close", close)
        if prev_close < level <= close:
            return 1.0  # Broke upward
        elif prev_close > level >= close:
            return 1.0  # Broke downward
        return 0.0


class RetestHolds(Detector):
    """Detects level retest that holds."""
    
    def __init__(self, timeframe: str = "5m", tolerance: float = 0.02):
        super().__init__(f"retest_holds_{timeframe}")
        self.timeframe = timeframe
        self.tolerance = tolerance
    
    def detect(self, bar: Dict[str, Any], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
        level = context.get("retest_level")
        if level is None:
            return 0.0
        
        low = bar.get("low", 0)
        close = bar.get("close", 0)
        
        # Price touched level but closed away
        if abs(low - level) / level < self.tolerance and close > level:
            return 1.0  # Bullish retest
        return 0.0


class RangeCompression(Detector):
    """Detects volatility compression (ATR/Range tightening)."""
    
    def __init__(self, timeframe: str = "5m", lookback: int = 20):
        super().__init__(f"range_compression_{timeframe}")
        self.lookback = lookback
    
    def detect(self, bar: Dict[str, Any], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
        atr = signals.get("T5", 0)  # Use ATR proxy
        atr_history = context.get("atr_history", [])
        
        if len(atr_history) < self.lookback:
            return 0.0
        
        # ATR is in bottom 20th percentile
        sorted_atr = sorted(atr_history[-self.lookback:])
        pctile_20 = sorted_atr[int(len(sorted_atr) * 0.2)]
        
        if atr <= pctile_20:
            return 1.0
        return 0.0


class ImpulseStrength(Detector):
    """Measures strength of directional move."""
    
    def __init__(self, timeframe: str = "5m"):
        super().__init__(f"impulse_strength_{timeframe}")
    
    def detect(self, bar: Dict[str, Any], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
        # Use momentum proxy (F5 momentum factor)
        momentum = signals.get("F5", 0.0)
        return max(0.0, min(1.0, abs(momentum)))


class VwapDeviation(Detector):
    """Measures z-score deviation from VWAP."""
    
    def __init__(self, threshold: float = 2.0):
        super().__init__(f"vwap_deviation_{threshold}")
        self.threshold = threshold
    
    def detect(self, bar: Dict[str, Any], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
        # Use value proxy (F4 value factor)
        value_score = signals.get("F4", 0.5)
        # If value score < 0.4, price is away from fair value
        deviation = abs(0.5 - value_score)
        return min(1.0, deviation * 2.0)  # Normalize


class SweepThenReject(Detector):
    """Detects liquidity sweep followed by rejection."""
    
    def __init__(self):
        super().__init__("sweep_then_reject")
    
    def detect(self, bar: Dict[str, Any], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
        # Check if current bar made new extreme then closed back inside
        high = bar.get("high", 0)
        low = bar.get("low", 0)
        close = bar.get("close", 0)
        
        prev_high = context.get("prev_high", high)
        prev_low = context.get("prev_low", low)
        
        # Swept high, closed below
        if high > prev_high and close < prev_high:
            return 1.0
        # Swept low, closed above
        if low < prev_low and close > prev_low:
            return 1.0
        
        return 0.0


class AbsorptionProxy(Detector):
    """Proxy for volume absorption (high volume, small range)."""
    
    def __init__(self, timeframe: str = "5m"):
        super().__init__(f"absorption_proxy_{timeframe}")
    
    def detect(self, bar: Dict[str, Any], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
        volume = bar.get("volume", 0)
        range_size = bar.get("high", 0) - bar.get("low", 0)
        
        avg_volume = context.get("avg_volume", volume)
        avg_range = context.get("avg_range", range_size)
        
        if avg_range == 0 or avg_volume == 0:
            return 0.0
        
        # High volume relative to average, small range relative to average
        volume_ratio = volume / avg_volume
        range_ratio = range_size / avg_range
        
        if volume_ratio > 1.5 and range_ratio < 0.5:
            return 1.0
        return 0.0


class DeltaDivergence(Detector):
    """Detects price vs volume/delta divergence."""
    
    def __init__(self, timeframe: str = "5m"):
        super().__init__(f"delta_divergence_{timeframe}")
    
    def detect(self, bar: Dict[str, Any], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
        # Price making new high, but momentum weakening
        close = bar.get("close", 0)
        prev_close = context.get("prev_close", close)
        
        momentum = signals.get("F5", 0.5)
        prev_momentum = context.get("prev_momentum", momentum)
        
        # Bearish divergence: price up, momentum down
        if close > prev_close and momentum < prev_momentum:
            return 1.0
        # Bullish divergence: price down, momentum up
        if close < prev_close and momentum > prev_momentum:
            return 1.0
        
        return 0.0


class SessionTransition(Detector):
    """Detects session transition windows."""
    
    def __init__(self, session: str):
        super().__init__(f"session_transition_{session}")
        self.session = session
    
    def detect(self, bar: Dict[str, Any], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
        current_session = context.get("current_session", "")
        if current_session == self.session:
            return 1.0
        return 0.0


class VolatilityExpansion(Detector):
    """Detects volatility breakout."""
    
    def __init__(self, threshold: float = 1.5):
        super().__init__(f"vol_expansion_{threshold}")
        self.threshold = threshold
    
    def detect(self, bar: Dict[str, Any], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
        current_atr = signals.get("T5", 0)
        avg_atr = context.get("avg_atr", current_atr)
        
        if avg_atr == 0:
            return 0.0
        
        ratio = current_atr / avg_atr
        if ratio > self.threshold:
            return 1.0
        return 0.0


# Detector registry
DETECTOR_REGISTRY: Dict[str, Detector] = {
    "breaks_level_high": BreaksLevel("high"),
    "breaks_level_low": BreaksLevel("low"),
    "retest_holds": RetestHolds(),
    "range_compression": RangeCompression(),
    "impulse_strength": ImpulseStrength(),
    "vwap_deviation": VwapDeviation(),
    "sweep_then_reject": SweepThenReject(),
    "absorption_proxy": AbsorptionProxy(),
    "delta_divergence": DeltaDivergence(),
    "session_transition_ny_open": SessionTransition("NY_OPEN"),
    "session_transition_london_open": SessionTransition("LONDON_OPEN"),
    "volatility_expansion": VolatilityExpansion(),
}


def get_detector(detector_id: str) -> Optional[Detector]:
    """Retrieve detector by ID."""
    return DETECTOR_REGISTRY.get(detector_id)
