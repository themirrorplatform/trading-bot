"""
Bias-Derived Signals (S29-S50+)
Signals derived from the 150 cognitive/market biases framework.

These signals augment the core 28 signals with bias-awareness:
- Psychological state indicators (FOMO, Panic, Herding)
- Structural bias detectors (Round numbers, Gamma, Anchoring)
- Temporal bias adjustments (Time-of-day, Day-of-week, Event proximity)
- Meta-cognition flags (Overconfidence, Recency, Confirmation)
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from collections import deque
import math
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


@dataclass
class BiasSignalOutput:
    """Output from bias signal computations"""
    # Psychological State (6 signals)
    fomo_index: float                    # S29: Fear of missing out indicator
    panic_index: float                   # S30: Capitulation/panic indicator
    herding_score: float                 # S31: Following the crowd indicator
    greed_index: float                   # S32: Overextension/greed indicator
    fear_index: float                    # S33: Excessive caution indicator
    euphoria_flag: float                 # S34: Blow-off top indicator

    # Structural Biases (6 signals)
    round_number_proximity: float        # S35: Distance to psychological levels
    gamma_exposure_proxy: float          # S36: Options-related pinning (Fri proxy)
    anchoring_level_distance: float      # S37: Distance from key anchor prices
    recency_bias_score: float            # S38: Over-weighting recent moves
    overnight_gap_bias: float            # S39: Gap fill probability
    opening_drive_exhaustion: float      # S40: First hour momentum exhaustion

    # Temporal Biases (6 signals)
    time_of_day_edge: float              # S41: Historical time-of-day performance
    day_of_week_edge: float              # S42: Historical day-of-week performance
    pre_event_compression: float         # S43: Volatility compression before events
    post_event_expansion: float          # S44: Volatility expansion after events
    month_end_flow: float                # S45: Month-end rebalancing bias
    quarter_end_flow: float              # S46: Quarter-end window dressing

    # Meta-Cognition (4 signals)
    overconfidence_flag: float           # S47: System showing overconfidence
    confirmation_bias_risk: float        # S48: Seeking confirming signals
    availability_bias_score: float       # S49: Over-weighting memorable events
    hindsight_trap_flag: float           # S50: Pattern seems obvious in retrospect

    # Aggregate scores
    psychological_state_score: float     # Aggregate psychological health
    structural_bias_score: float         # Aggregate structural bias presence
    temporal_bias_score: float           # Aggregate temporal factors
    meta_cognition_score: float          # Aggregate meta-awareness

    timestamp: datetime


class BiasSignalEngine:
    """
    Computes bias-derived signals from market data and system state.

    These signals don't generate entries directly - they modify thresholds
    and provide additional context for the belief engine.
    """

    def __init__(self, tick_size: Decimal = Decimal("0.25")):
        self.tick_size = tick_size

        # Historical tracking for bias detection
        self._recent_trades: deque = deque(maxlen=50)  # Recent trade outcomes
        self._price_history: deque = deque(maxlen=100)
        self._volume_history: deque = deque(maxlen=100)
        self._volatility_history: deque = deque(maxlen=50)

        # Key levels for anchoring
        self._session_open: Optional[Decimal] = None
        self._session_high: Optional[Decimal] = None
        self._session_low: Optional[Decimal] = None
        self._prev_close: Optional[Decimal] = None
        self._vwap: Optional[Decimal] = None

        # Win/loss tracking for meta-cognition
        self._consecutive_wins: int = 0
        self._consecutive_losses: int = 0
        self._recent_pnl: deque = deque(maxlen=20)

        # Round number levels (computed dynamically)
        self._round_levels: List[Decimal] = []

    def compute_bias_signals(
        self,
        timestamp: datetime,
        close: Decimal,
        high: Decimal,
        low: Decimal,
        volume: int,
        atr_14: Optional[Decimal],
        vol_z: Optional[float],
        vwap: Optional[Decimal],
        session_phase: int,
        micro_trend_5: Optional[float],
        climax_bar_flag: Optional[float],
        hhll_trend_strength: Optional[float],
        range_compression: Optional[float],
        dvs: float = 1.0,
        eqs: float = 1.0,
        current_position: int = 0,
        recent_trade_outcomes: Optional[List[float]] = None
    ) -> BiasSignalOutput:
        """
        Compute all bias-derived signals.

        Args:
            timestamp: Current bar timestamp
            close: Close price
            high: High price
            low: Low price
            volume: Volume
            atr_14: ATR(14) from signal engine
            vol_z: Volume z-score from signal engine
            vwap: VWAP from signal engine
            session_phase: Session phase (0-6)
            micro_trend_5: 5-bar momentum from signal engine
            climax_bar_flag: Climax volume flag
            hhll_trend_strength: Trend strength
            range_compression: Range compression ratio
            dvs: Data validity score
            eqs: Execution quality score
            current_position: Current position (0, 1, -1)
            recent_trade_outcomes: Recent trade P&L for meta-cognition

        Returns:
            BiasSignalOutput with all bias signals
        """
        # Ensure timezone
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=ET)

        # Update state
        self._update_state(close, high, low, volume, atr_14, vwap, timestamp)
        if recent_trade_outcomes:
            for outcome in recent_trade_outcomes:
                self._update_trade_outcome(outcome)

        # ===== PSYCHOLOGICAL STATE SIGNALS =====
        fomo_index = self._compute_fomo_index(
            close, vol_z, micro_trend_5, hhll_trend_strength, current_position
        )
        panic_index = self._compute_panic_index(
            close, vol_z, micro_trend_5, climax_bar_flag
        )
        herding_score = self._compute_herding_score(
            vol_z, micro_trend_5, hhll_trend_strength
        )
        greed_index = self._compute_greed_index(
            close, hhll_trend_strength, range_compression, atr_14
        )
        fear_index = self._compute_fear_index(
            range_compression, vol_z, micro_trend_5
        )
        euphoria_flag = self._compute_euphoria_flag(
            vol_z, hhll_trend_strength, climax_bar_flag
        )

        # ===== STRUCTURAL BIAS SIGNALS =====
        round_number_proximity = self._compute_round_number_proximity(close, atr_14)
        gamma_exposure_proxy = self._compute_gamma_exposure_proxy(timestamp, close)
        anchoring_level_distance = self._compute_anchoring_distance(close, atr_14)
        recency_bias_score = self._compute_recency_bias_score()
        overnight_gap_bias = self._compute_overnight_gap_bias(close, session_phase)
        opening_drive_exhaustion = self._compute_opening_drive_exhaustion(
            timestamp, session_phase, micro_trend_5, vol_z
        )

        # ===== TEMPORAL BIAS SIGNALS =====
        time_of_day_edge = self._compute_time_of_day_edge(timestamp)
        day_of_week_edge = self._compute_day_of_week_edge(timestamp)
        pre_event_compression = self._compute_pre_event_compression(
            timestamp, range_compression
        )
        post_event_expansion = self._compute_post_event_expansion(
            timestamp, atr_14
        )
        month_end_flow = self._compute_month_end_flow(timestamp)
        quarter_end_flow = self._compute_quarter_end_flow(timestamp)

        # ===== META-COGNITION SIGNALS =====
        overconfidence_flag = self._compute_overconfidence_flag()
        confirmation_bias_risk = self._compute_confirmation_bias_risk(current_position)
        availability_bias_score = self._compute_availability_bias_score()
        hindsight_trap_flag = self._compute_hindsight_trap_flag(
            hhll_trend_strength, micro_trend_5
        )

        # ===== AGGREGATE SCORES =====
        psychological_state_score = self._aggregate_psychological(
            fomo_index, panic_index, herding_score,
            greed_index, fear_index, euphoria_flag
        )
        structural_bias_score = self._aggregate_structural(
            round_number_proximity, gamma_exposure_proxy,
            anchoring_level_distance, recency_bias_score,
            overnight_gap_bias, opening_drive_exhaustion
        )
        temporal_bias_score = self._aggregate_temporal(
            time_of_day_edge, day_of_week_edge,
            pre_event_compression, post_event_expansion,
            month_end_flow, quarter_end_flow
        )
        meta_cognition_score = self._aggregate_meta(
            overconfidence_flag, confirmation_bias_risk,
            availability_bias_score, hindsight_trap_flag
        )

        return BiasSignalOutput(
            # Psychological
            fomo_index=fomo_index,
            panic_index=panic_index,
            herding_score=herding_score,
            greed_index=greed_index,
            fear_index=fear_index,
            euphoria_flag=euphoria_flag,
            # Structural
            round_number_proximity=round_number_proximity,
            gamma_exposure_proxy=gamma_exposure_proxy,
            anchoring_level_distance=anchoring_level_distance,
            recency_bias_score=recency_bias_score,
            overnight_gap_bias=overnight_gap_bias,
            opening_drive_exhaustion=opening_drive_exhaustion,
            # Temporal
            time_of_day_edge=time_of_day_edge,
            day_of_week_edge=day_of_week_edge,
            pre_event_compression=pre_event_compression,
            post_event_expansion=post_event_expansion,
            month_end_flow=month_end_flow,
            quarter_end_flow=quarter_end_flow,
            # Meta
            overconfidence_flag=overconfidence_flag,
            confirmation_bias_risk=confirmation_bias_risk,
            availability_bias_score=availability_bias_score,
            hindsight_trap_flag=hindsight_trap_flag,
            # Aggregates
            psychological_state_score=psychological_state_score,
            structural_bias_score=structural_bias_score,
            temporal_bias_score=temporal_bias_score,
            meta_cognition_score=meta_cognition_score,
            timestamp=timestamp
        )

    # ==================== STATE MANAGEMENT ====================

    def _update_state(
        self,
        close: Decimal,
        high: Decimal,
        low: Decimal,
        volume: int,
        atr_14: Optional[Decimal],
        vwap: Optional[Decimal],
        timestamp: datetime
    ):
        """Update internal state for bias tracking"""
        self._price_history.append(float(close))
        self._volume_history.append(volume)
        if atr_14:
            self._volatility_history.append(float(atr_14))

        # Update session levels
        if self._session_high is None or high > self._session_high:
            self._session_high = high
        if self._session_low is None or low < self._session_low:
            self._session_low = low

        self._vwap = vwap

        # Update round number levels based on price
        self._update_round_levels(close)

    def _update_round_levels(self, close: Decimal):
        """Compute relevant round number levels"""
        base = int(close)
        self._round_levels = [
            Decimal(str(base - 100)),
            Decimal(str(base - 50)),
            Decimal(str(base)),
            Decimal(str(base + 50)),
            Decimal(str(base + 100)),
        ]
        # Add quarter levels
        for offset in [-25, 25, 75, -75]:
            self._round_levels.append(Decimal(str(base + offset)))

    def _update_trade_outcome(self, pnl: float):
        """Update trade outcome tracking for meta-cognition"""
        self._recent_pnl.append(pnl)
        if pnl > 0:
            self._consecutive_wins += 1
            self._consecutive_losses = 0
        elif pnl < 0:
            self._consecutive_losses += 1
            self._consecutive_wins = 0

    def set_session_open(self, price: Decimal):
        """Set session open price for anchoring"""
        self._session_open = price

    def set_prev_close(self, price: Decimal):
        """Set previous close for gap calculations"""
        self._prev_close = price

    def reset_session(self):
        """Reset session-specific state"""
        self._session_open = None
        self._session_high = None
        self._session_low = None
        self._vwap = None

    # ==================== PSYCHOLOGICAL STATE SIGNALS ====================

    def _compute_fomo_index(
        self,
        close: Decimal,
        vol_z: Optional[float],
        micro_trend_5: Optional[float],
        hhll_trend_strength: Optional[float],
        current_position: int
    ) -> float:
        """
        S29: FOMO Index - Fear of missing out

        High FOMO = market moving strongly, you're not in, volume surging
        """
        if vol_z is None or micro_trend_5 is None:
            return 0.0

        # FOMO increases when:
        # 1. Strong directional move (high abs(micro_trend))
        # 2. High volume (vol_z > 1)
        # 3. You're flat (position = 0)
        # 4. Trend strength is high

        trend_strength = abs(micro_trend_5) if micro_trend_5 else 0.0
        volume_surge = max(0, vol_z) if vol_z else 0.0
        flat_multiplier = 1.5 if current_position == 0 else 0.5
        hhll = abs(hhll_trend_strength) if hhll_trend_strength else 0.0

        fomo = (trend_strength * 0.4 + volume_surge * 0.3 + hhll * 0.3) * flat_multiplier
        return max(0.0, min(1.0, fomo))

    def _compute_panic_index(
        self,
        close: Decimal,
        vol_z: Optional[float],
        micro_trend_5: Optional[float],
        climax_bar_flag: Optional[float]
    ) -> float:
        """
        S30: Panic Index - Capitulation indicator

        High panic = sharp down move + climax volume + trend breakdown
        """
        if vol_z is None or micro_trend_5 is None:
            return 0.0

        # Panic increases when:
        # 1. Sharp downward move (micro_trend << 0)
        # 2. Climax volume
        # 3. Breaking down from recent levels

        down_move = max(0, -micro_trend_5) if micro_trend_5 else 0.0
        volume_climax = climax_bar_flag if climax_bar_flag else 0.0
        volume_surge = max(0, vol_z - 1) / 2 if vol_z else 0.0

        panic = down_move * 0.5 + volume_climax * 0.3 + volume_surge * 0.2
        return max(0.0, min(1.0, panic))

    def _compute_herding_score(
        self,
        vol_z: Optional[float],
        micro_trend_5: Optional[float],
        hhll_trend_strength: Optional[float]
    ) -> float:
        """
        S31: Herding Score - Following the crowd

        High herding = everyone piling in same direction
        """
        if vol_z is None or micro_trend_5 is None:
            return 0.0

        # Herding high when:
        # 1. Trend and volume aligned
        # 2. Consistent directional bars

        trend_vol_alignment = 0.0
        if micro_trend_5 and vol_z:
            # Same sign = aligned
            if (micro_trend_5 > 0 and vol_z > 0) or (micro_trend_5 < 0 and vol_z > 0):
                trend_vol_alignment = min(abs(micro_trend_5), vol_z / 2)

        hhll = abs(hhll_trend_strength) if hhll_trend_strength else 0.0

        herding = trend_vol_alignment * 0.6 + hhll * 0.4
        return max(0.0, min(1.0, herding))

    def _compute_greed_index(
        self,
        close: Decimal,
        hhll_trend_strength: Optional[float],
        range_compression: Optional[float],
        atr_14: Optional[Decimal]
    ) -> float:
        """
        S32: Greed Index - Overextension indicator

        High greed = extended move, low compression (stretched)
        """
        if hhll_trend_strength is None:
            return 0.0

        # Greed high when:
        # 1. Strong uptrend (hhll > 0.7)
        # 2. Range expanding (compression > 1)
        # 3. Far from mean

        trend_extended = max(0, hhll_trend_strength - 0.5) * 2 if hhll_trend_strength else 0.0
        range_exp = max(0, (range_compression or 1.0) - 1.0)

        greed = trend_extended * 0.6 + range_exp * 0.4
        return max(0.0, min(1.0, greed))

    def _compute_fear_index(
        self,
        range_compression: Optional[float],
        vol_z: Optional[float],
        micro_trend_5: Optional[float]
    ) -> float:
        """
        S33: Fear Index - Excessive caution

        High fear = tight ranges, low volume, indecision
        """
        # Fear high when:
        # 1. Range compression (tight bars)
        # 2. Low volume
        # 3. No clear direction

        tight_range = max(0, 1.0 - (range_compression or 1.0))
        low_volume = max(0, -(vol_z or 0))
        no_direction = 1.0 - abs(micro_trend_5 or 0)

        fear = tight_range * 0.4 + low_volume * 0.3 + no_direction * 0.3
        return max(0.0, min(1.0, fear))

    def _compute_euphoria_flag(
        self,
        vol_z: Optional[float],
        hhll_trend_strength: Optional[float],
        climax_bar_flag: Optional[float]
    ) -> float:
        """
        S34: Euphoria Flag - Blow-off top indicator

        Euphoria = extreme extension + climax volume + exhaustion signs
        """
        # Euphoria when:
        # 1. Very strong uptrend
        # 2. Climax volume
        # 3. Extended move

        extreme_trend = 1.0 if (hhll_trend_strength or 0) > 0.8 else 0.0
        climax = climax_bar_flag or 0.0
        volume_extreme = 1.0 if (vol_z or 0) > 2.5 else 0.0

        euphoria = (extreme_trend + climax + volume_extreme) / 3.0
        return max(0.0, min(1.0, euphoria))

    # ==================== STRUCTURAL BIAS SIGNALS ====================

    def _compute_round_number_proximity(
        self,
        close: Decimal,
        atr_14: Optional[Decimal]
    ) -> float:
        """
        S35: Round Number Proximity

        How close to psychological round numbers (00, 50, etc.)
        Returns 1.0 when very close, 0.0 when far
        """
        if not self._round_levels or atr_14 is None or atr_14 == 0:
            return 0.5

        # Find closest round level
        min_distance = float('inf')
        for level in self._round_levels:
            distance = abs(close - level)
            if distance < min_distance:
                min_distance = distance

        # Normalize by ATR - close = within 0.5 ATR
        proximity = 1.0 - min(1.0, float(Decimal(str(min_distance)) / atr_14))
        return max(0.0, min(1.0, proximity))

    def _compute_gamma_exposure_proxy(
        self,
        timestamp: datetime,
        close: Decimal
    ) -> float:
        """
        S36: Gamma Exposure Proxy

        Options-related pinning effect, strongest on Fridays and monthly expiry
        """
        weekday = timestamp.weekday()  # 0=Mon, 4=Fri
        day = timestamp.day

        # Friday effect
        friday_weight = 1.0 if weekday == 4 else 0.3

        # Monthly expiry (3rd Friday approximation: days 15-21)
        monthly_expiry = 1.0 if (weekday == 4 and 15 <= day <= 21) else 0.0

        # Combine with round number (options cluster at round strikes)
        round_prox = self._compute_round_number_proximity(close, Decimal("5"))

        gamma = friday_weight * 0.5 + monthly_expiry * 0.3 + round_prox * 0.2
        return max(0.0, min(1.0, gamma))

    def _compute_anchoring_distance(
        self,
        close: Decimal,
        atr_14: Optional[Decimal]
    ) -> float:
        """
        S37: Anchoring Level Distance

        Distance from key anchor levels (session open, prev close, VWAP)
        Lower = closer to anchors = more likely to act as support/resistance
        """
        if atr_14 is None or atr_14 == 0:
            return 0.5

        distances = []

        if self._session_open:
            distances.append(abs(close - self._session_open))
        if self._prev_close:
            distances.append(abs(close - self._prev_close))
        if self._vwap:
            distances.append(abs(close - self._vwap))

        if not distances:
            return 0.5

        min_distance = min(distances)
        # Normalize: close = within 0.5 ATR
        proximity = 1.0 - min(1.0, float(Decimal(str(min_distance)) / atr_14))
        return max(0.0, min(1.0, proximity))

    def _compute_recency_bias_score(self) -> float:
        """
        S38: Recency Bias Score

        Over-weighting of recent price action vs longer history
        High = recent moves dominating, potentially misleading
        """
        if len(self._price_history) < 20:
            return 0.5

        prices = list(self._price_history)

        # Compare recent 5-bar move to 20-bar move
        recent_5 = prices[-1] - prices[-5] if len(prices) >= 5 else 0
        longer_20 = prices[-1] - prices[-20] if len(prices) >= 20 else 0

        # If recent move is disproportionate to longer trend
        if longer_20 == 0:
            return 0.5

        recency_ratio = abs(recent_5 / longer_20) if longer_20 != 0 else 1.0

        # High ratio = recent dominates = high recency bias
        return max(0.0, min(1.0, recency_ratio - 0.5))

    def _compute_overnight_gap_bias(
        self,
        close: Decimal,
        session_phase: int
    ) -> float:
        """
        S39: Overnight Gap Bias

        Gap fill probability based on gap size and session progress
        """
        if self._prev_close is None or session_phase not in [1, 2]:
            return 0.0

        gap = close - self._prev_close
        gap_pct = abs(float(gap / self._prev_close)) * 100

        # Large gaps have higher fill probability
        if gap_pct < 0.1:
            return 0.0
        elif gap_pct < 0.3:
            return 0.3
        elif gap_pct < 0.5:
            return 0.6
        else:
            return 0.8

    def _compute_opening_drive_exhaustion(
        self,
        timestamp: datetime,
        session_phase: int,
        micro_trend_5: Optional[float],
        vol_z: Optional[float]
    ) -> float:
        """
        S40: Opening Drive Exhaustion

        First hour momentum running out of steam
        """
        if session_phase != 1:  # Only in opening phase
            return 0.0

        t = timestamp.time()
        minutes_since_open = (t.hour - 9) * 60 + t.minute - 30

        # Exhaustion more likely later in opening phase
        time_factor = min(1.0, minutes_since_open / 60.0)

        # Volume declining = exhaustion
        vol_declining = max(0, -(vol_z or 0))

        # Trend weakening
        trend_weak = 1.0 - abs(micro_trend_5 or 0)

        exhaustion = time_factor * 0.4 + vol_declining * 0.3 + trend_weak * 0.3
        return max(0.0, min(1.0, exhaustion))

    # ==================== TEMPORAL BIAS SIGNALS ====================

    def _compute_time_of_day_edge(self, timestamp: datetime) -> float:
        """
        S41: Time of Day Edge

        Historical edge by time of day (simplified model)
        Higher = better historical performance
        """
        t = timestamp.time()

        # Simplified time-of-day edge model
        # Best: 10:00-11:00, 14:00-15:00
        # Worst: 12:00-13:00 (lunch)
        # Moderate: Opening, Close

        if time(10, 0) <= t < time(11, 0):
            return 0.8  # Mid-morning sweet spot
        elif time(14, 0) <= t < time(15, 0):
            return 0.75  # Afternoon momentum
        elif time(9, 30) <= t < time(10, 0):
            return 0.5  # Opening volatility
        elif time(15, 0) <= t < time(15, 45):
            return 0.6  # Pre-close
        elif time(11, 30) <= t < time(13, 30):
            return 0.2  # Lunch doldrums
        else:
            return 0.4  # Other times

    def _compute_day_of_week_edge(self, timestamp: datetime) -> float:
        """
        S42: Day of Week Edge

        Historical edge by day of week (simplified model)
        """
        weekday = timestamp.weekday()

        # Simplified model:
        # Tuesday, Wednesday, Thursday: Best
        # Monday: Moderate (gap effects)
        # Friday: Lower (position squaring)

        edges = {
            0: 0.5,   # Monday
            1: 0.7,   # Tuesday
            2: 0.75,  # Wednesday
            3: 0.7,   # Thursday
            4: 0.4,   # Friday
        }
        return edges.get(weekday, 0.5)

    def _compute_pre_event_compression(
        self,
        timestamp: datetime,
        range_compression: Optional[float]
    ) -> float:
        """
        S43: Pre-Event Compression

        Volatility compression before known events (FOMC, etc.)
        Note: Simplified - would need event calendar integration
        """
        # Check for FOMC-like compression (Wednesdays around 14:00)
        weekday = timestamp.weekday()
        t = timestamp.time()

        fomc_day = weekday == 2  # Wednesday
        pre_fomc_time = time(12, 0) <= t < time(14, 0)

        compression = range_compression if range_compression else 1.0

        if fomc_day and pre_fomc_time and compression < 0.7:
            return 0.8  # High pre-event compression
        elif compression < 0.5:
            return 0.5  # General compression
        else:
            return 0.0

    def _compute_post_event_expansion(
        self,
        timestamp: datetime,
        atr_14: Optional[Decimal]
    ) -> float:
        """
        S44: Post-Event Expansion

        Volatility expansion after events
        """
        weekday = timestamp.weekday()
        t = timestamp.time()

        # Post-FOMC (Wednesday 14:30+)
        post_fomc = weekday == 2 and t >= time(14, 30)

        # Check for vol spike
        if len(self._volatility_history) < 10:
            return 0.0

        recent_vol = list(self._volatility_history)[-5:]
        older_vol = list(self._volatility_history)[-10:-5]

        avg_recent = sum(recent_vol) / len(recent_vol) if recent_vol else 0
        avg_older = sum(older_vol) / len(older_vol) if older_vol else 1

        vol_expansion = (avg_recent / avg_older) - 1 if avg_older > 0 else 0

        if post_fomc and vol_expansion > 0.5:
            return 0.9
        elif vol_expansion > 0.3:
            return 0.5
        else:
            return 0.0

    def _compute_month_end_flow(self, timestamp: datetime) -> float:
        """
        S45: Month End Flow

        Rebalancing effects near month end
        """
        day = timestamp.day

        # Last 3 trading days of month (simplified: days 28-31)
        if day >= 28:
            return 0.7
        elif day >= 25:
            return 0.3
        else:
            return 0.0

    def _compute_quarter_end_flow(self, timestamp: datetime) -> float:
        """
        S46: Quarter End Flow

        Window dressing and rebalancing at quarter end
        """
        month = timestamp.month
        day = timestamp.day

        # Quarter end months: 3, 6, 9, 12
        quarter_end_month = month in [3, 6, 9, 12]

        if quarter_end_month and day >= 25:
            return 0.8
        elif quarter_end_month and day >= 20:
            return 0.4
        else:
            return 0.0

    # ==================== META-COGNITION SIGNALS ====================

    def _compute_overconfidence_flag(self) -> float:
        """
        S47: Overconfidence Flag

        System showing signs of overconfidence (winning streak)
        """
        # Overconfidence after consecutive wins
        if self._consecutive_wins >= 4:
            return 0.9
        elif self._consecutive_wins >= 3:
            return 0.6
        elif self._consecutive_wins >= 2:
            return 0.3
        else:
            return 0.0

    def _compute_confirmation_bias_risk(self, current_position: int) -> float:
        """
        S48: Confirmation Bias Risk

        Risk of seeking confirming signals for current position
        """
        # Higher risk when in a position and recent P&L is positive
        if current_position == 0:
            return 0.0

        if len(self._recent_pnl) < 3:
            return 0.3  # Unknown, moderate risk

        recent_positive = sum(1 for p in list(self._recent_pnl)[-3:] if p > 0)

        if recent_positive >= 2:
            return 0.7  # Likely to seek confirmation
        else:
            return 0.3

    def _compute_availability_bias_score(self) -> float:
        """
        S49: Availability Bias Score

        Over-weighting memorable/recent events
        """
        if len(self._recent_pnl) < 5:
            return 0.5

        pnl_list = list(self._recent_pnl)

        # Check for extreme recent outcomes
        recent = pnl_list[-3:]
        extreme_recent = any(abs(p) > 2 * sum(abs(x) for x in pnl_list) / len(pnl_list)
                           for p in recent)

        return 0.7 if extreme_recent else 0.3

    def _compute_hindsight_trap_flag(
        self,
        hhll_trend_strength: Optional[float],
        micro_trend_5: Optional[float]
    ) -> float:
        """
        S50: Hindsight Trap Flag

        Pattern that looks obvious in retrospect but wasn't predictable
        """
        # Strong trend + momentum alignment = "obvious" in hindsight
        trend = abs(hhll_trend_strength or 0)
        momentum = abs(micro_trend_5 or 0)

        if trend > 0.7 and momentum > 0.7:
            return 0.8  # Looks "obvious" - beware hindsight
        elif trend > 0.5 and momentum > 0.5:
            return 0.4
        else:
            return 0.0

    # ==================== AGGREGATION ====================

    def _aggregate_psychological(
        self, fomo: float, panic: float, herding: float,
        greed: float, fear: float, euphoria: float
    ) -> float:
        """Aggregate psychological health score (lower = healthier)"""
        # Average of extremes
        return (fomo + panic + herding + greed + fear + euphoria) / 6.0

    def _aggregate_structural(
        self, round_prox: float, gamma: float, anchor: float,
        recency: float, gap: float, exhaustion: float
    ) -> float:
        """Aggregate structural bias presence"""
        return (round_prox + gamma + anchor + recency + gap + exhaustion) / 6.0

    def _aggregate_temporal(
        self, tod: float, dow: float, pre_event: float,
        post_event: float, month_end: float, quarter_end: float
    ) -> float:
        """Aggregate temporal factor score (higher = better time to trade)"""
        # TOD and DOW are edge scores (higher = better)
        # Others are event scores (higher = more caution)
        edge = (tod + dow) / 2.0
        caution = (pre_event + post_event + month_end + quarter_end) / 4.0
        return edge - (caution * 0.3)  # Reduce edge by caution factors

    def _aggregate_meta(
        self, overconf: float, confirm: float,
        avail: float, hindsight: float
    ) -> float:
        """Aggregate meta-cognition score (lower = more self-aware)"""
        return (overconf + confirm + avail + hindsight) / 4.0
