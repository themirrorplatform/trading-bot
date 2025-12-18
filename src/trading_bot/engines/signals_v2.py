"""
Signal Engine v2 - Complete 28-Signal Implementation
Implements all signals from signal_dictionary.yaml with reliability scoring.

Categories:
1. Price Structure & Volatility (12 signals)
2. Volume & Participation (9 signals) 
3. Session Context (4 signals)
4. Quality & Cost (3 signals)
"""

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional, Dict, Any, List
from decimal import Decimal
from collections import deque
import math
from zoneinfo import ZoneInfo

# America/New_York timezone for all session logic
ET = ZoneInfo("America/New_York")


@dataclass
class SignalReliability:
    """Reliability metadata for signals"""
    dvs_ok: bool
    eqs_ok: bool  
    session_ok: bool
    overall_score: float  # 0.0-1.0


@dataclass
class SignalOutput:
    """Complete signal output with all 28 signals + reliability"""
    # Price Structure & Volatility (12)
    vwap_z: Optional[float]
    vwap_slope: Optional[float]
    atr_14_n: Optional[float]
    range_compression: Optional[float]
    hhll_trend_strength: Optional[float]
    breakout_distance_n: Optional[float]
    rejection_wick_n: Optional[float]
    close_location_value: Optional[float]
    gap_from_prev_close_n: Optional[float]
    distance_from_poc_proxy: Optional[float]
    micro_trend_5: Optional[float]
    real_body_impulse_n: Optional[float]
    
    # Volume & Participation (9)
    vol_z: Optional[float]
    vol_slope_20: Optional[float]
    effort_vs_result: Optional[float]
    range_expansion_on_volume: Optional[float]
    climax_bar_flag: Optional[float]
    quiet_bar_flag: Optional[float]
    consecutive_high_vol_bars: Optional[float]
    participation_expansion_index: Optional[float]
    
    # Session Context (4)
    session_phase: int
    opening_range_break: Optional[float]
    lunch_void_gate: float
    close_magnet_index: Optional[float]
    
    # Quality & Cost (3)
    spread_proxy_tickiness: Optional[float]
    slippage_risk_proxy: Optional[float]
    friction_regime_index: Optional[float]
    
    # DVS is computed externally but included for completeness
    dvs: float
    
    # Metadata
    reliability: SignalReliability
    timestamp: datetime


class SignalEngineV2:
    """
    Complete signal engine implementing all 28 signals from signal_dictionary.yaml.
    """
    
    def __init__(
        self, 
        tick_size: Decimal = Decimal("0.25"),
        lookback_vol: int = 20,
        lookback_prices: int = 30
    ):
        self.tick_size = tick_size
        self.lookback_vol = lookback_vol
        self.lookback_prices = lookback_prices
        
        # VWAP state (resets at 09:30 RTH)
        self._vwap_sum_pv: Decimal = Decimal("0")
        self._vwap_sum_v: int = 0
        self._last_rth_date: Optional[str] = None
        
        # Price history for various calculations
        self._closes: deque = deque(maxlen=lookback_prices)
        self._highs: deque = deque(maxlen=lookback_prices)
        self._lows: deque = deque(maxlen=lookback_prices)
        self._typical_prices: deque = deque(maxlen=lookback_prices)
        
        # Volume history
        self._volumes: deque = deque(maxlen=lookback_vol)
        
        # ATR(14) and ATR(30) with Wilder smoothing
        self._atr14: Optional[Decimal] = None
        self._atr30: Optional[Decimal] = None
        self._atr14_warmup: int = 0
        self._atr30_warmup: int = 0
        self._tr_accumulator14: Decimal = Decimal("0")
        self._tr_accumulator30: Decimal = Decimal("0")
        self._prior_close: Optional[Decimal] = None
        
        # VWAP history for slope calculation (last 5 bars)
        self._vwap_history: deque = deque(maxlen=5)
        
        # Session opening range tracking
        self._opening_range_high: Optional[Decimal] = None
        self._opening_range_low: Optional[Decimal] = None
        self._opening_range_set: bool = False
        
        # Consecutive high volume bars counter
        self._consecutive_high_vol_count: int = 0
        
        # Micro trend (5-bar close comparison)
        self._close_history_5: deque = deque(maxlen=5)
        
        # Time-of-day ATR median tracking (for normalization)
        # Simplified: use fixed reference ATR for now
        self._reference_atr: Optional[Decimal] = None
        
    def get_session_phase(self, current_time: datetime) -> int:
        """
        Determine session phase per session.yaml.
        
        Returns phase code:
        0: PRE_MARKET (before 09:30)
        1: OPENING (09:30 <= t < 10:30)
        2: MID_MORNING (10:30 <= t < 11:30)
        3: LUNCH (11:30 <= t < 13:30)
        4: AFTERNOON (13:30 <= t < 15:00)
        5: CLOSE (15:00 <= t < 16:00)
        6: POST_RTH (>= 16:00)
        """
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=ET)
        elif current_time.tzinfo != ET:
            current_time = current_time.astimezone(ET)
        
        t = current_time.time()
        
        if t < time(9, 30):
            return 0
        elif t < time(10, 30):
            return 1
        elif t < time(11, 30):
            return 2
        elif t < time(13, 30):
            return 3
        elif t < time(15, 0):
            return 4
        elif t < time(16, 0):
            return 5
        else:
            return 6
    
    def compute_signals(
        self,
        timestamp: datetime,
        open_price: Decimal,
        high: Decimal,
        low: Decimal,
        close: Decimal,
        volume: int,
        bid: Optional[Decimal] = None,
        ask: Optional[Decimal] = None,
        dvs: float = 1.0,
        eqs: float = 1.0
    ) -> SignalOutput:
        """
        Compute all 28 signals for current bar.
        
        Args:
            timestamp: Bar timestamp
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Volume
            bid: Current bid (for spread)
            ask: Current ask (for spread)
            dvs: Data Validity Score (0-1)
            eqs: Execution Quality Score (0-1)
        
        Returns:
            SignalOutput with all 28 signals + reliability
        """
        # Ensure timezone-aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=ET)
        elif timestamp.tzinfo != ET:
            timestamp = timestamp.astimezone(ET)
        
        # Get session phase
        phase = self.get_session_phase(timestamp)
        
        # Update historical data
        self._update_history(open_price, high, low, close, volume)
        
        # ===== PRICE STRUCTURE & VOLATILITY SIGNALS (12) =====
        
        # 1. VWAP_Z: Distance from VWAP in ATR units
        vwap = self._update_vwap(timestamp, high, low, close, volume)
        vwap_z = self._compute_vwap_z(close, vwap)
        
        # 2. VWAP_Slope: Rate of change of VWAP
        vwap_slope = self._compute_vwap_slope()
        
        # 3. ATR_14_N: Normalized ATR(14)
        atr_result = self._update_atrs(high, low, close)
        atr_14_n = self._normalize_atr(atr_result["atr14"])
        
        # 4. RangeCompression: Current range vs recent average range
        range_compression = self._compute_range_compression(high, low)
        
        # 5. HHLL_TrendStrength: Higher highs/lower lows pattern
        hhll_trend = self._compute_hhll_trend_strength()
        
        # 6. BreakoutDistance_N: Distance beyond recent high/low in ATR units
        breakout_dist = self._compute_breakout_distance_n(high, low, atr_result["atr14"])
        
        # 7. RejectionWick_N: Wick size vs body size, normalized by ATR
        rejection_wick = self._compute_rejection_wick_n(open_price, high, low, close, atr_result["atr14"])
        
        # 8. CloseLocationValue: Where close is within bar range
        close_loc = self._compute_close_location_value(high, low, close)
        
        # 9. GapFromPrevClose_N: Gap size normalized by ATR
        gap_n = self._compute_gap_from_prev_close_n(open_price, atr_result["atr14"])
        
        # 10. DistanceFromPOC_Proxy: Proxy for distance from volume POC
        poc_dist = self._compute_distance_from_poc_proxy(close)
        
        # 11. MicroTrend_5: 5-bar close momentum
        micro_trend = self._compute_micro_trend_5()
        
        # 12. RealBodyImpulse_N: Body size vs recent body sizes
        body_impulse = self._compute_real_body_impulse_n(open_price, close)
        
        # ===== VOLUME & PARTICIPATION SIGNALS (9) =====
        
        # 13. Vol_Z: Volume Z-score (normalized deviation from mean)
        vol_z = self._compute_vol_z(volume)
        
        # 14. Vol_Slope_20: Rate of change of volume
        vol_slope = self._compute_vol_slope_20()
        
        # 15. EffortVsResult: Volume relative to price range
        evr = self._compute_effort_vs_result(volume, high, low)
        
        # 16. RangeExpansionOnVolume: Range increase with volume increase
        range_exp_vol = self._compute_range_expansion_on_volume(volume, high, low)
        
        # 17. ClimaxBar_Flag: Extreme volume bar
        climax_flag = self._compute_climax_bar_flag(volume)
        
        # 18. QuietBar_Flag: Very low volume bar
        quiet_flag = self._compute_quiet_bar_flag(volume)
        
        # 19. ConsecutiveHighVolBars: Count of consecutive high volume bars
        consec_high_vol = self._compute_consecutive_high_vol_bars(volume)
        
        # 20. ParticipationExpansionIndex: Volume increase with price expansion
        participation_idx = self._compute_participation_expansion_index(volume, high, low)
        
        # ===== SESSION CONTEXT SIGNALS (4) =====
        
        # 21. SessionPhase: Already computed (0-6)
        
        # 22. OpeningRangeBreak: Break of first hour range
        or_break = self._compute_opening_range_break(timestamp, high, low, close, phase)
        
        # 23. LunchVoidGate: Hard gate for lunch period
        lunch_gate = 0.0 if phase == 3 else 1.0
        
        # 24. CloseMagnetIndex: Proximity to session close
        close_magnet = self._compute_close_magnet_index(timestamp)
        
        # ===== QUALITY & COST SIGNALS (3) =====
        
        # 25. SpreadProxy_Tickiness: Bid-ask spread quality
        spread_proxy = self._compute_spread_proxy(bid, ask)
        
        # 26. SlippageRiskProxy: Expected slippage based on volume/ATR
        slippage_proxy = self._compute_slippage_risk_proxy(volume, atr_result["atr14"])
        
        # 27. FrictionRegimeIndex: Overall cost regime
        friction_idx = self._compute_friction_regime_index(spread_proxy, slippage_proxy, atr_result["atr14"])
        
        # ===== RELIABILITY SCORING =====
        
        reliability = self._compute_reliability(dvs, eqs, phase)
        
        return SignalOutput(
            # Price Structure & Volatility
            vwap_z=vwap_z,
            vwap_slope=vwap_slope,
            atr_14_n=atr_14_n,
            range_compression=range_compression,
            hhll_trend_strength=hhll_trend,
            breakout_distance_n=breakout_dist,
            rejection_wick_n=rejection_wick,
            close_location_value=close_loc,
            gap_from_prev_close_n=gap_n,
            distance_from_poc_proxy=poc_dist,
            micro_trend_5=micro_trend,
            real_body_impulse_n=body_impulse,
            
            # Volume & Participation
            vol_z=vol_z,
            vol_slope_20=vol_slope,
            effort_vs_result=evr,
            range_expansion_on_volume=range_exp_vol,
            climax_bar_flag=climax_flag,
            quiet_bar_flag=quiet_flag,
            consecutive_high_vol_bars=consec_high_vol,
            participation_expansion_index=participation_idx,
            
            # Session Context
            session_phase=phase,
            opening_range_break=or_break,
            lunch_void_gate=lunch_gate,
            close_magnet_index=close_magnet,
            
            # Quality & Cost
            spread_proxy_tickiness=spread_proxy,
            slippage_risk_proxy=slippage_proxy,
            friction_regime_index=friction_idx,
            
            # DVS (computed externally, passed in)
            dvs=dvs,
            
            # Metadata
            reliability=reliability,
            timestamp=timestamp
        )
    
    # ========== INTERNAL COMPUTATION METHODS ==========
    
    def _update_history(self, open_price: Decimal, high: Decimal, low: Decimal, close: Decimal, volume: int):
        """Update price and volume history"""
        self._closes.append(close)
        self._highs.append(high)
        self._lows.append(low)
        typical_price = (high + low + close) / Decimal("3")
        self._typical_prices.append(typical_price)
        self._volumes.append(volume)
        self._close_history_5.append(close)
    
    def _update_vwap(self, timestamp: datetime, high: Decimal, low: Decimal, close: Decimal, volume: int) -> Optional[Decimal]:
        """Update VWAP (resets at 09:30 RTH open)"""
        t = timestamp.time()
        rth_date = timestamp.strftime("%Y-%m-%d")
        is_rth = time(9, 30) <= t < time(16, 0)
        
        if not is_rth:
            return None
        
        # Reset at 09:30 on new trading day
        if self._last_rth_date != rth_date:
            self._vwap_sum_pv = Decimal("0")
            self._vwap_sum_v = 0
            self._last_rth_date = rth_date
            self._opening_range_high = None
            self._opening_range_low = None
            self._opening_range_set = False
        
        typical_price = (high + low + close) / Decimal("3")
        self._vwap_sum_pv += typical_price * Decimal(volume)
        self._vwap_sum_v += volume
        
        if self._vwap_sum_v == 0:
            return None
        
        vwap = self._vwap_sum_pv / Decimal(self._vwap_sum_v)
        self._vwap_history.append(vwap)
        return vwap
    
    def _compute_vwap_z(self, close: Decimal, vwap: Optional[Decimal]) -> Optional[float]:
        """VWAP_Z: Distance from VWAP in ATR units"""
        if vwap is None or self._atr14 is None:
            return None
        distance = close - vwap
        z_score = float(distance / self._atr14) if self._atr14 > 0 else 0.0
        return max(-3.0, min(3.0, z_score))  # Clamped to [-3, 3]
    
    def _compute_vwap_slope(self) -> Optional[float]:
        """VWAP_Slope: Rate of change of VWAP (5-bar linear fit)"""
        if len(self._vwap_history) < 5:
            return None
        
        # Simple linear regression slope
        n = len(self._vwap_history)
        x_mean = (n - 1) / 2.0
        y_mean = sum(float(v) for v in self._vwap_history) / n
        
        numerator = sum((i - x_mean) * (float(self._vwap_history[i]) - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        # Normalize by tick size to make scale-independent
        return max(-1.0, min(1.0, slope / float(self.tick_size)))
    
    def _update_atrs(self, high: Decimal, low: Decimal, close: Decimal) -> Dict[str, Optional[Decimal]]:
        """Update ATR(14) and ATR(30) using Wilder smoothing"""
        prior_close = self._prior_close
        tr = self._compute_true_range(high, low, prior_close)
        
        # ATR(14)
        atr14_out = None
        if self._atr14 is None:
            self._atr14_warmup += 1
            if self._atr14_warmup < 14:
                self._tr_accumulator14 += tr
            else:
                self._atr14 = (self._tr_accumulator14 + tr) / Decimal("14")
                atr14_out = self._atr14
                if self._reference_atr is None:
                    self._reference_atr = self._atr14
        else:
            self._atr14 = (self._atr14 * Decimal("13") + tr) / Decimal("14")
            atr14_out = self._atr14
        
        # ATR(30)
        atr30_out = None
        if self._atr30 is None:
            self._atr30_warmup += 1
            if self._atr30_warmup < 30:
                self._tr_accumulator30 += tr
            else:
                self._atr30 = (self._tr_accumulator30 + tr) / Decimal("30")
                atr30_out = self._atr30
        else:
            self._atr30 = (self._atr30 * Decimal("29") + tr) / Decimal("30")
            atr30_out = self._atr30
        
        self._prior_close = close
        return {"tr": tr, "atr14": atr14_out, "atr30": atr30_out}
    
    def _compute_true_range(self, high: Decimal, low: Decimal, prior_close: Optional[Decimal]) -> Decimal:
        """True range calculation"""
        if prior_close is None:
            return high - low
        return max(high - low, abs(high - prior_close), abs(low - prior_close))
    
    def _normalize_atr(self, atr14: Optional[Decimal]) -> Optional[float]:
        """ATR_14_N: Normalized ATR(14) relative to reference"""
        if atr14 is None or self._reference_atr is None or self._reference_atr == 0:
            return None
        ratio = float(atr14 / self._reference_atr)
        return max(0.0, min(2.0, ratio))  # Clamped to [0, 2]
    
    def _compute_range_compression(self, high: Decimal, low: Decimal) -> Optional[float]:
        """RangeCompression: Current range vs recent average range"""
        if len(self._highs) < 10:
            return None
        
        current_range = high - low
        avg_range = sum(self._highs[i] - self._lows[i] for i in range(-10, 0)) / Decimal("10")
        
        if avg_range == 0:
            return 0.0
        
        compression = float(current_range / avg_range)
        return max(0.0, min(2.0, compression))
    
    def _compute_hhll_trend_strength(self) -> Optional[float]:
        """HHLL_TrendStrength: Higher highs / lower lows pattern"""
        if len(self._highs) < 10 or len(self._lows) < 10:
            return None
        
        recent_highs = list(self._highs)[-10:]
        recent_lows = list(self._lows)[-10:]
        
        # Count higher highs
        hh_count = sum(1 for i in range(1, 10) if recent_highs[i] > recent_highs[i-1])
        # Count lower lows
        ll_count = sum(1 for i in range(1, 10) if recent_lows[i] < recent_lows[i-1])
        
        # Trend strength: +1 for strong uptrend, -1 for strong downtrend
        strength = (hh_count - ll_count) / 9.0
        return max(-1.0, min(1.0, strength))
    
    def _compute_breakout_distance_n(self, high: Decimal, low: Decimal, atr14: Optional[Decimal]) -> Optional[float]:
        """BreakoutDistance_N: Distance beyond recent high/low in ATR units"""
        if len(self._highs) < 20 or atr14 is None or atr14 == 0:
            return None
        
        recent_high = max(self._highs)
        recent_low = min(self._lows)
        
        # Distance beyond range
        if high > recent_high:
            distance = high - recent_high
        elif low < recent_low:
            distance = low - recent_low  # Negative
        else:
            distance = Decimal("0")
        
        normalized = float(distance / atr14)
        return max(-2.0, min(2.0, normalized))
    
    def _compute_rejection_wick_n(self, open_price: Decimal, high: Decimal, low: Decimal, close: Decimal, atr14: Optional[Decimal]) -> Optional[float]:
        """RejectionWick_N: Wick size vs body size, normalized by ATR"""
        if atr14 is None or atr14 == 0:
            return None
        
        body = abs(close - open_price)
        upper_wick = high - max(open_price, close)
        lower_wick = min(open_price, close) - low
        
        # Max wick as rejection signal
        max_wick = max(upper_wick, lower_wick)
        
        if body == 0:
            # Doji: pure wick
            rejection = float(max_wick / atr14)
        else:
            # Wick vs body ratio
            rejection = float((max_wick - body) / atr14)
        
        return max(-1.0, min(1.0, rejection))
    
    def _compute_close_location_value(self, high: Decimal, low: Decimal, close: Decimal) -> Optional[float]:
        """CloseLocationValue: Where close is within bar range [0, 1]"""
        bar_range = high - low
        if bar_range == 0:
            return 0.5  # Neutral if no range
        
        location = float((close - low) / bar_range)
        return max(0.0, min(1.0, location))
    
    def _compute_gap_from_prev_close_n(self, open_price: Decimal, atr14: Optional[Decimal]) -> Optional[float]:
        """GapFromPrevClose_N: Gap size normalized by ATR"""
        if self._prior_close is None or atr14 is None or atr14 == 0:
            return None
        
        gap = open_price - self._prior_close
        normalized_gap = float(gap / atr14)
        return max(-2.0, min(2.0, normalized_gap))
    
    def _compute_distance_from_poc_proxy(self, close: Decimal) -> Optional[float]:
        """DistanceFromPOC_Proxy: Proxy using VWAP as POC approximation"""
        if len(self._typical_prices) < 20:
            return None
        
        # Use median of recent typical prices as POC proxy
        sorted_prices = sorted(self._typical_prices)
        median_price = sorted_prices[len(sorted_prices) // 2]
        
        if self._atr14 is None or self._atr14 == 0:
            return None
        
        distance = close - median_price
        normalized = float(distance / self._atr14)
        return max(-2.0, min(2.0, normalized))
    
    def _compute_micro_trend_5(self) -> Optional[float]:
        """MicroTrend_5: 5-bar close momentum"""
        if len(self._close_history_5) < 5:
            return None
        
        closes = list(self._close_history_5)
        # Count up bars
        up_count = sum(1 for i in range(1, 5) if closes[i] > closes[i-1])
        # Trend: +1 for all up, -1 for all down
        trend = (up_count - 2) / 2.0  # Scale to [-1, 1]
        return max(-1.0, min(1.0, trend))
    
    def _compute_real_body_impulse_n(self, open_price: Decimal, close: Decimal) -> Optional[float]:
        """RealBodyImpulse_N: Body size vs recent body sizes"""
        # Need last 11 closes to compute 10 prior body changes safely
        if len(self._closes) < 11:
            return None
        
        current_body = abs(close - open_price)
        
        # Average body magnitude of last 10 bars using consecutive close differences
        closes = list(self._closes)[-11:]
        recent_bodies = [abs(closes[i] - closes[i-1]) for i in range(1, len(closes))]
        if not recent_bodies:
            return 0.0
        
        avg_body = sum(recent_bodies) / len(recent_bodies)
        
        if avg_body == 0:
            return 0.0
        
        impulse = float(current_body / avg_body)
        return max(0.0, min(3.0, impulse))
    
    # ========== VOLUME SIGNALS ==========
    
    def _compute_vol_z(self, volume: int) -> Optional[float]:
        """Vol_Z: Volume Z-score"""
        if len(self._volumes) < 20:
            return None
        
        volumes = list(self._volumes)
        mean_vol = sum(volumes) / len(volumes)
        std_vol = math.sqrt(sum((v - mean_vol) ** 2 for v in volumes) / len(volumes))
        
        if std_vol == 0:
            return 0.0
        
        z_score = (volume - mean_vol) / std_vol
        return max(-3.0, min(3.0, z_score))
    
    def _compute_vol_slope_20(self) -> Optional[float]:
        """Vol_Slope_20: Rate of change of volume"""
        if len(self._volumes) < 20:
            return None
        
        volumes = list(self._volumes)
        n = len(volumes)
        x_mean = (n - 1) / 2.0
        y_mean = sum(volumes) / n
        
        numerator = sum((i - x_mean) * (volumes[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0 or y_mean == 0:
            return 0.0
        
        slope = numerator / denominator
        # Normalize by mean volume
        normalized_slope = slope / y_mean
        return max(-1.0, min(1.0, normalized_slope))
    
    def _compute_effort_vs_result(self, volume: int, high: Decimal, low: Decimal) -> Optional[float]:
        """EffortVsResult: Volume relative to price range"""
        if len(self._volumes) < 10:
            return None
        
        bar_range = high - low
        if bar_range == 0:
            return 0.0
        
        avg_vol = sum(self._volumes) / len(self._volumes)
        if avg_vol == 0:
            return 0.0
        
        avg_range = sum(self._highs[i] - self._lows[i] for i in range(-10, 0)) / Decimal("10")
        if avg_range == 0:
            return 0.0
        
        # Effort (volume) vs Result (range)
        evr = float(volume / avg_vol) - float(bar_range / avg_range)
        return max(-1.0, min(1.0, evr))
    
    def _compute_range_expansion_on_volume(self, volume: int, high: Decimal, low: Decimal) -> Optional[float]:
        """RangeExpansionOnVolume: Range increase with volume increase"""
        if len(self._volumes) < 10 or len(self._highs) < 10:
            return None
        
        current_range = high - low
        avg_range = sum(self._highs[i] - self._lows[i] for i in range(-10, 0)) / Decimal("10")
        avg_vol = sum(self._volumes) / len(self._volumes)
        
        if avg_range == 0 or avg_vol == 0:
            return 0.0
        
        range_ratio = float(current_range / avg_range)
        vol_ratio = volume / avg_vol
        
        # Both expanding together
        expansion = (range_ratio * vol_ratio) - 1.0
        return max(-1.0, min(2.0, expansion))
    
    def _compute_climax_bar_flag(self, volume: int) -> Optional[float]:
        """ClimaxBar_Flag: Extreme volume bar (>2.5 std above mean)"""
        if len(self._volumes) < 20:
            return None
        
        volumes = list(self._volumes)
        mean_vol = sum(volumes) / len(volumes)
        std_vol = math.sqrt(sum((v - mean_vol) ** 2 for v in volumes) / len(volumes))
        
        if std_vol == 0:
            return 0.0
        
        z_score = (volume - mean_vol) / std_vol
        return 1.0 if z_score > 2.5 else 0.0
    
    def _compute_quiet_bar_flag(self, volume: int) -> Optional[float]:
        """QuietBar_Flag: Very low volume bar (<-1.5 std below mean)"""
        if len(self._volumes) < 20:
            return None
        
        volumes = list(self._volumes)
        mean_vol = sum(volumes) / len(volumes)
        std_vol = math.sqrt(sum((v - mean_vol) ** 2 for v in volumes) / len(volumes))
        
        if std_vol == 0:
            return 0.0
        
        z_score = (volume - mean_vol) / std_vol
        return 1.0 if z_score < -1.5 else 0.0
    
    def _compute_consecutive_high_vol_bars(self, volume: int) -> Optional[float]:
        """ConsecutiveHighVolBars: Count of consecutive high volume bars"""
        if len(self._volumes) < 10:
            return None
        
        avg_vol = sum(self._volumes) / len(self._volumes)
        threshold = avg_vol * 1.5
        
        if volume > threshold:
            self._consecutive_high_vol_count += 1
        else:
            self._consecutive_high_vol_count = 0
        
        # Normalize to [0, 1] with saturation at 5
        return min(1.0, self._consecutive_high_vol_count / 5.0)
    
    def _compute_participation_expansion_index(self, volume: int, high: Decimal, low: Decimal) -> Optional[float]:
        """ParticipationExpansionIndex: Volume increase with price expansion"""
        if len(self._volumes) < 10 or len(self._highs) < 10:
            return None
        
        # Similar to RangeExpansionOnVolume but focused on participation
        avg_vol = sum(self._volumes) / len(self._volumes)
        current_range = high - low
        avg_range = sum(self._highs[i] - self._lows[i] for i in range(-10, 0)) / Decimal("10")
        
        if avg_vol == 0 or avg_range == 0:
            return 0.0
        
        vol_expansion = (volume / avg_vol) - 1.0
        range_expansion = float((current_range / avg_range) - Decimal("1.0"))
        
        # Product of expansions
        participation = vol_expansion * range_expansion
        return max(-1.0, min(2.0, participation))
    
    # ========== SESSION CONTEXT SIGNALS ==========
    
    def _compute_opening_range_break(self, timestamp: datetime, high: Decimal, low: Decimal, close: Decimal, phase: int) -> Optional[float]:
        """OpeningRangeBreak: Break of first hour range"""
        # Set opening range during phase 1 (09:30-10:30)
        if phase == 1:
            if self._opening_range_high is None:
                self._opening_range_high = high
                self._opening_range_low = low
            else:
                self._opening_range_high = max(self._opening_range_high, high)
                self._opening_range_low = min(self._opening_range_low, low)
            self._opening_range_set = False
            return 0.0  # No break during formation
        
        # Mark range as set after phase 1
        if phase > 1 and not self._opening_range_set:
            self._opening_range_set = True
        
        # Check for break after phase 1
        if not self._opening_range_set or self._opening_range_high is None or self._opening_range_low is None:
            return 0.0
        
        if close > self._opening_range_high:
            return 1.0  # Upside break
        elif close < self._opening_range_low:
            return -1.0  # Downside break
        else:
            return 0.0  # No break
    
    def _compute_close_magnet_index(self, timestamp: datetime) -> Optional[float]:
        """CloseMagnetIndex: Proximity to session close"""
        t = timestamp.time()
        
        # Calculate minutes until 16:00 close
        current_minutes = t.hour * 60 + t.minute
        close_minutes = 16 * 60
        
        minutes_to_close = close_minutes - current_minutes
        
        if minutes_to_close <= 0:
            return 0.0  # After close
        
        # Magnet effect increases in last 30 minutes
        if minutes_to_close > 30:
            return 0.0
        
        # Linear increase from 0 to 1 over last 30 minutes
        magnet = 1.0 - (minutes_to_close / 30.0)
        return max(0.0, min(1.0, magnet))
    
    # ========== QUALITY & COST SIGNALS ==========
    
    def _compute_spread_proxy(self, bid: Optional[Decimal], ask: Optional[Decimal]) -> Optional[float]:
        """SpreadProxy_Tickiness: Bid-ask spread quality"""
        if bid is None or ask is None or ask <= bid:
            return None
        
        spread_price = ask - bid
        spread_ticks = spread_price / self.tick_size
        
        # Normalize: 1 tick = ideal, >3 ticks = poor
        if spread_ticks <= 1:
            return 1.0  # Tight
        elif spread_ticks >= 3:
            return 0.0  # Wide
        else:
            return 1.0 - float((spread_ticks - Decimal("1")) / Decimal("2"))
    
    def _compute_slippage_risk_proxy(self, volume: int, atr14: Optional[Decimal]) -> Optional[float]:
        """SlippageRiskProxy: Expected slippage based on volume/ATR"""
        if len(self._volumes) < 20 or atr14 is None or atr14 == 0:
            return None
        
        avg_vol = sum(self._volumes) / len(self._volumes)
        vol_ratio = volume / avg_vol if avg_vol > 0 else 1.0
        
        # Low volume + high ATR = high slippage risk
        # High volume + low ATR = low slippage risk
        if self._reference_atr is None or self._reference_atr == 0:
            atr_ratio = 1.0
        else:
            atr_ratio = float(atr14 / self._reference_atr)
        
        # Risk increases with ATR, decreases with volume
        risk = atr_ratio / vol_ratio
        
        # Normalize to [0, 1] where 0 = low risk, 1 = high risk
        normalized_risk = min(1.0, risk / 2.0)
        return 1.0 - normalized_risk  # Invert so higher = better
    
    def _compute_friction_regime_index(self, spread_proxy: Optional[float], slippage_proxy: Optional[float], atr14: Optional[Decimal]) -> Optional[float]:
        """FrictionRegimeIndex: Overall cost regime"""
        if spread_proxy is None or slippage_proxy is None:
            return None
        
        # Combine spread and slippage
        avg_quality = (spread_proxy + slippage_proxy) / 2.0
        
        # Adjust for volatility regime
        if atr14 is not None and self._reference_atr is not None and self._reference_atr > 0:
            atr_ratio = float(atr14 / self._reference_atr)
            # Higher ATR = higher friction
            friction = avg_quality / atr_ratio
        else:
            friction = avg_quality
        
        return max(0.0, min(1.0, friction))
    
    # ========== RELIABILITY SCORING ==========
    
    def _compute_reliability(self, dvs: float, eqs: float, phase: int) -> SignalReliability:
        """Compute signal reliability based on DVS, EQS, and session context"""
        dvs_ok = dvs >= 0.80
        eqs_ok = eqs >= 0.75
        session_ok = phase not in [0, 3, 6]  # Not in pre-market, lunch, or post-RTH
        
        # Overall score: weighted combination
        score = (dvs * 0.4 + eqs * 0.3 + (1.0 if session_ok else 0.0) * 0.3)
        
        return SignalReliability(
            dvs_ok=dvs_ok,
            eqs_ok=eqs_ok,
            session_ok=session_ok,
            overall_score=score
        )
    
    def reset_session_state(self):
        """Reset all session-dependent state"""
        self._vwap_sum_pv = Decimal("0")
        self._vwap_sum_v = 0
        self._last_rth_date = None
        self._vwap_history.clear()
        self._opening_range_high = None
        self._opening_range_low = None
        self._opening_range_set = False
        self._consecutive_high_vol_count = 0
