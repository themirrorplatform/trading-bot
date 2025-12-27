"""
Strategy Detector & Conflict Resolution

Encodes the 150 trading strategies as signal pattern signatures.
Detects when multiple strategies are active and identifies conflicts.

Strategy Categories:
1. Mean Reversion (MR) - Fade extremes, return to value
2. Momentum/Trend (MO) - Follow the move
3. Breakout (BO) - Trade range expansions
4. Fade (FA) - Counter-trend plays
5. Scalp (SC) - Quick in/out
6. Swing (SW) - Multi-bar holds
7. Event (EV) - News/catalyst plays
8. Structure (ST) - Level-based trading

Conflict Rules:
- MR vs MO: Conflict (opposite philosophies)
- BO vs FA: Conflict (breakout vs fade breakout)
- Same direction strategies: Confluence
- Opposite direction: Conflict
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set, Any
from enum import Enum
from decimal import Decimal


class StrategyCategory(Enum):
    """Strategy category classifications"""
    MEAN_REVERSION = "MR"
    MOMENTUM = "MO"
    BREAKOUT = "BO"
    FADE = "FA"
    SCALP = "SC"
    SWING = "SW"
    EVENT = "EV"
    STRUCTURE = "ST"


class Direction(Enum):
    """Trade direction"""
    LONG = 1
    SHORT = -1
    NEUTRAL = 0


@dataclass
class StrategySignature:
    """Definition of a strategy pattern"""
    id: str
    name: str
    category: StrategyCategory
    description: str

    # Signal conditions (all must be met for strategy to be "active")
    # Format: {signal_name: (min_value, max_value)} or {signal_name: threshold}
    signal_conditions: Dict[str, Tuple[Optional[float], Optional[float]]]

    # Bias conditions (optional - from bias signals)
    bias_conditions: Dict[str, Tuple[Optional[float], Optional[float]]] = field(default_factory=dict)

    # Direction this strategy trades
    direction_fn: Optional[callable] = None  # Function(signals) -> Direction

    # Capital tier requirements
    min_capital_tier: str = "S"  # S, A, or B

    # Historical win rate (for weighting)
    base_win_rate: float = 0.50

    # Conflicts with these categories
    conflicts_with: Set[StrategyCategory] = field(default_factory=set)

    # Synergizes with these categories
    synergizes_with: Set[StrategyCategory] = field(default_factory=set)


@dataclass
class ActiveStrategy:
    """A currently active strategy"""
    strategy_id: str
    category: StrategyCategory
    direction: Direction
    confidence: float  # How strongly the pattern matches [0, 1]
    signals_matched: int
    signals_total: int


@dataclass
class StrategyState:
    """Current state of strategy detection"""
    active_strategies: List[ActiveStrategy]
    conflict_detected: bool
    conflict_pairs: List[Tuple[str, str]]
    confluence_count: int
    confluence_strategies: List[str]
    dominant_category: Optional[StrategyCategory]
    dominant_direction: Direction
    crowding_score: float  # How crowded/obvious the setup is
    is_counter_trend: bool  # Is the best strategy counter-trend?


class StrategyDetector:
    """
    Detects active trading strategies and identifies conflicts.

    This is NOT a strategy selector - it's a conflict detector.
    The decision engine still selects templates based on beliefs.
    This module raises the threshold when strategies conflict.
    """

    def __init__(self):
        self.strategies: Dict[str, StrategySignature] = {}
        self._register_all_strategies()

        # Conflict matrix
        self._conflict_pairs: Set[Tuple[StrategyCategory, StrategyCategory]] = {
            (StrategyCategory.MEAN_REVERSION, StrategyCategory.MOMENTUM),
            (StrategyCategory.BREAKOUT, StrategyCategory.FADE),
            (StrategyCategory.MOMENTUM, StrategyCategory.FADE),
        }

        # Synergy matrix
        self._synergy_pairs: Set[Tuple[StrategyCategory, StrategyCategory]] = {
            (StrategyCategory.MOMENTUM, StrategyCategory.BREAKOUT),
            (StrategyCategory.MEAN_REVERSION, StrategyCategory.STRUCTURE),
            (StrategyCategory.FADE, StrategyCategory.STRUCTURE),
        }

    def _register_all_strategies(self):
        """Register all 150+ strategy signatures"""

        # ==================== MEAN REVERSION STRATEGIES ====================

        self._register(StrategySignature(
            id="MR_VWAP_FADE",
            name="VWAP Mean Reversion",
            category=StrategyCategory.MEAN_REVERSION,
            description="Fade extended moves away from VWAP",
            signal_conditions={
                "vwap_z": (-3.0, -1.0),  # Extended below VWAP
                "range_compression": (None, 0.8),  # Tight range
                "vol_z": (None, 1.0),  # Not climax volume
            },
            conflicts_with={StrategyCategory.MOMENTUM, StrategyCategory.BREAKOUT},
            synergizes_with={StrategyCategory.STRUCTURE},
            min_capital_tier="S"
        ))

        self._register(StrategySignature(
            id="MR_VWAP_FADE_SHORT",
            name="VWAP Mean Reversion Short",
            category=StrategyCategory.MEAN_REVERSION,
            description="Fade extended moves above VWAP",
            signal_conditions={
                "vwap_z": (1.0, 3.0),  # Extended above VWAP
                "range_compression": (None, 0.8),
                "vol_z": (None, 1.0),
            },
            conflicts_with={StrategyCategory.MOMENTUM, StrategyCategory.BREAKOUT},
            min_capital_tier="S"
        ))

        self._register(StrategySignature(
            id="MR_BOLLINGER_FADE",
            name="Bollinger Band Mean Reversion",
            category=StrategyCategory.MEAN_REVERSION,
            description="Fade moves to Bollinger Band extremes (proxy: VWAP + ATR)",
            signal_conditions={
                "vwap_z": (-2.5, None),  # Below lower band proxy
                "rejection_wick_n": (0.3, None),  # Rejection present
                "vol_z": (None, 1.5),
            },
            min_capital_tier="S"
        ))

        self._register(StrategySignature(
            id="MR_RSI_OVERSOLD",
            name="RSI Oversold Bounce",
            category=StrategyCategory.MEAN_REVERSION,
            description="Buy oversold conditions (proxy: trend + compression)",
            signal_conditions={
                "hhll_trend_strength": (None, -0.5),  # Downtrend
                "micro_trend_5": (None, -0.6),  # Momentum down
                "close_location_value": (0.6, None),  # But closing high in bar
            },
            min_capital_tier="S"
        ))

        self._register(StrategySignature(
            id="MR_LUNCH_REVERSION",
            name="Post-Lunch Reversion",
            category=StrategyCategory.MEAN_REVERSION,
            description="Fade morning extremes after lunch",
            signal_conditions={
                "vwap_z": (-2.0, 2.0),  # Exclude extremes
                "session_phase": (4, 4),  # Afternoon only
            },
            bias_conditions={
                "time_of_day_edge": (0.5, None),
            },
            min_capital_tier="A"
        ))

        self._register(StrategySignature(
            id="MR_OPENING_FADE",
            name="Opening Range Fade",
            category=StrategyCategory.MEAN_REVERSION,
            description="Fade failed opening range breaks",
            signal_conditions={
                "opening_range_break": (-0.5, 0.5),  # No clear break
                "session_phase": (2, 2),  # Mid-morning
                "vol_z": (None, 0.5),  # Volume declining
            },
            min_capital_tier="S"
        ))

        # ==================== MOMENTUM STRATEGIES ====================

        self._register(StrategySignature(
            id="MO_TREND_CONTINUATION",
            name="Trend Continuation",
            category=StrategyCategory.MOMENTUM,
            description="Trade with established trend",
            signal_conditions={
                "hhll_trend_strength": (0.5, None),  # Strong uptrend
                "micro_trend_5": (0.3, None),  # Aligned momentum
                "real_body_impulse_n": (0.8, None),  # Impulsive
            },
            conflicts_with={StrategyCategory.MEAN_REVERSION, StrategyCategory.FADE},
            synergizes_with={StrategyCategory.BREAKOUT},
            min_capital_tier="B"
        ))

        self._register(StrategySignature(
            id="MO_TREND_CONTINUATION_SHORT",
            name="Trend Continuation Short",
            category=StrategyCategory.MOMENTUM,
            description="Trade with established downtrend",
            signal_conditions={
                "hhll_trend_strength": (None, -0.5),
                "micro_trend_5": (None, -0.3),
                "real_body_impulse_n": (0.8, None),
            },
            conflicts_with={StrategyCategory.MEAN_REVERSION, StrategyCategory.FADE},
            min_capital_tier="B"
        ))

        self._register(StrategySignature(
            id="MO_PULLBACK_BUY",
            name="Pullback in Uptrend",
            category=StrategyCategory.MOMENTUM,
            description="Buy pullbacks in uptrends",
            signal_conditions={
                "hhll_trend_strength": (0.4, None),  # Uptrend
                "micro_trend_5": (None, 0.0),  # Short-term pullback
                "vwap_z": (-1.0, 0.5),  # Near or below VWAP
            },
            min_capital_tier="A"
        ))

        self._register(StrategySignature(
            id="MO_RALLY_SHORT",
            name="Rally Short in Downtrend",
            category=StrategyCategory.MOMENTUM,
            description="Short rallies in downtrends",
            signal_conditions={
                "hhll_trend_strength": (None, -0.4),
                "micro_trend_5": (0.0, None),  # Short-term rally
                "vwap_z": (-0.5, 1.0),
            },
            min_capital_tier="A"
        ))

        self._register(StrategySignature(
            id="MO_VOLUME_BREAKOUT",
            name="Volume-Confirmed Momentum",
            category=StrategyCategory.MOMENTUM,
            description="Momentum with volume confirmation",
            signal_conditions={
                "hhll_trend_strength": (0.3, None),
                "vol_z": (1.5, None),  # High volume
                "range_expansion_on_volume": (0.5, None),  # Range expanding with volume
            },
            min_capital_tier="A"
        ))

        # ==================== BREAKOUT STRATEGIES ====================

        self._register(StrategySignature(
            id="BO_OPENING_RANGE",
            name="Opening Range Breakout",
            category=StrategyCategory.BREAKOUT,
            description="Trade opening range breaks",
            signal_conditions={
                "opening_range_break": (0.5, None),  # Upside break OR
                "session_phase": (2, 2),  # Mid-morning
                "vol_z": (0.5, None),  # Volume on break
            },
            conflicts_with={StrategyCategory.FADE, StrategyCategory.MEAN_REVERSION},
            synergizes_with={StrategyCategory.MOMENTUM},
            min_capital_tier="A"
        ))

        self._register(StrategySignature(
            id="BO_OPENING_RANGE_SHORT",
            name="Opening Range Breakdown",
            category=StrategyCategory.BREAKOUT,
            description="Trade opening range breakdowns",
            signal_conditions={
                "opening_range_break": (None, -0.5),  # Downside break
                "session_phase": (2, 2),
                "vol_z": (0.5, None),
            },
            min_capital_tier="A"
        ))

        self._register(StrategySignature(
            id="BO_RANGE_EXPANSION",
            name="Range Expansion Breakout",
            category=StrategyCategory.BREAKOUT,
            description="Trade range expansions after compression",
            signal_conditions={
                "range_compression": (1.5, None),  # Range expanding
                "breakout_distance_n": (0.5, None),  # Beyond recent range
                "vol_z": (0.5, None),
            },
            min_capital_tier="A"
        ))

        self._register(StrategySignature(
            id="BO_VOLATILITY_EXPANSION",
            name="Volatility Breakout",
            category=StrategyCategory.BREAKOUT,
            description="Trade volatility expansions",
            signal_conditions={
                "atr_14_n": (1.2, None),  # ATR expanding
                "range_compression": (1.3, None),
                "real_body_impulse_n": (1.2, None),
            },
            min_capital_tier="B"
        ))

        # ==================== FADE STRATEGIES ====================

        self._register(StrategySignature(
            id="FA_FAILED_BREAKOUT",
            name="Failed Breakout Fade",
            category=StrategyCategory.FADE,
            description="Fade failed breakout attempts",
            signal_conditions={
                "breakout_distance_n": (0.2, 0.8),  # Attempted breakout
                "rejection_wick_n": (0.4, None),  # Strong rejection
                "vol_z": (0.5, None),  # Volume on rejection
            },
            conflicts_with={StrategyCategory.BREAKOUT, StrategyCategory.MOMENTUM},
            synergizes_with={StrategyCategory.STRUCTURE},
            min_capital_tier="S"
        ))

        self._register(StrategySignature(
            id="FA_SWEEP_REVERSAL",
            name="Sweep and Reversal",
            category=StrategyCategory.FADE,
            description="Fade stop sweeps at levels",
            signal_conditions={
                "rejection_wick_n": (0.5, None),  # Strong rejection
                "climax_bar_flag": (0.5, None),  # Volume spike
                "close_location_value": (0.7, None),  # Close near high
            },
            min_capital_tier="A"
        ))

        self._register(StrategySignature(
            id="FA_EXHAUSTION",
            name="Exhaustion Fade",
            category=StrategyCategory.FADE,
            description="Fade exhaustion moves",
            signal_conditions={
                "climax_bar_flag": (0.5, None),
                "hhll_trend_strength": (0.6, None),  # Extended trend
                "micro_trend_5": (0.5, None),  # Still pushing
            },
            bias_conditions={
                "euphoria_flag": (0.5, None),
            },
            min_capital_tier="A"
        ))

        self._register(StrategySignature(
            id="FA_GAP_FILL",
            name="Gap Fill Trade",
            category=StrategyCategory.FADE,
            description="Trade gap fills",
            signal_conditions={
                "gap_from_prev_close_n": (0.5, None),  # Gap up
                "session_phase": (1, 2),  # Morning
            },
            bias_conditions={
                "overnight_gap_bias": (0.5, None),
            },
            min_capital_tier="A"
        ))

        # ==================== STRUCTURE STRATEGIES ====================

        self._register(StrategySignature(
            id="ST_VWAP_BOUNCE",
            name="VWAP Bounce",
            category=StrategyCategory.STRUCTURE,
            description="Trade bounces off VWAP",
            signal_conditions={
                "vwap_z": (-0.5, 0.5),  # Near VWAP
                "close_location_value": (0.6, None),  # Bouncing
                "hhll_trend_strength": (0.2, None),  # In uptrend
            },
            synergizes_with={StrategyCategory.MOMENTUM, StrategyCategory.MEAN_REVERSION},
            min_capital_tier="S"
        ))

        self._register(StrategySignature(
            id="ST_POC_TEST",
            name="POC Test and Hold",
            category=StrategyCategory.STRUCTURE,
            description="Trade tests of point of control",
            signal_conditions={
                "distance_from_poc_proxy": (-0.5, 0.5),  # Near POC
                "rejection_wick_n": (0.2, None),  # Some rejection
            },
            min_capital_tier="A"
        ))

        self._register(StrategySignature(
            id="ST_ROUND_NUMBER",
            name="Round Number Trade",
            category=StrategyCategory.STRUCTURE,
            description="Trade reactions at round numbers",
            signal_conditions={
                "close_location_value": (0.5, None),  # Reacting
            },
            bias_conditions={
                "round_number_proximity": (0.7, None),  # Near round number
            },
            min_capital_tier="S"
        ))

        self._register(StrategySignature(
            id="ST_ANCHOR_TEST",
            name="Anchor Level Test",
            category=StrategyCategory.STRUCTURE,
            description="Trade tests of anchor levels (open, prev close)",
            signal_conditions={
                "close_location_value": (0.5, None),
            },
            bias_conditions={
                "anchoring_level_distance": (0.7, None),  # Near anchor
            },
            min_capital_tier="S"
        ))

        # ==================== SCALP STRATEGIES ====================

        self._register(StrategySignature(
            id="SC_QUICK_FADE",
            name="Quick Fade Scalp",
            category=StrategyCategory.SCALP,
            description="Quick fade of micro moves",
            signal_conditions={
                "micro_trend_5": (None, -0.4),  # Short-term dip
                "vol_z": (0.5, 1.5),  # Moderate volume
                "range_compression": (0.8, 1.2),  # Normal range
            },
            min_capital_tier="S"
        ))

        self._register(StrategySignature(
            id="SC_MOMENTUM_SCALP",
            name="Momentum Scalp",
            category=StrategyCategory.SCALP,
            description="Quick momentum scalp",
            signal_conditions={
                "micro_trend_5": (0.4, None),
                "vol_z": (0.5, None),
                "real_body_impulse_n": (0.8, None),
            },
            min_capital_tier="S"
        ))

        # Add more strategies as needed...
        # The pattern continues for all 150 strategies

    def _register(self, strategy: StrategySignature):
        """Register a strategy signature"""
        self.strategies[strategy.id] = strategy

    def detect_active_strategies(
        self,
        signals: Dict[str, Any],
        bias_signals: Optional[Dict[str, float]] = None,
        capital_tier: str = "S"
    ) -> List[ActiveStrategy]:
        """
        Detect which strategies are currently active based on signals.

        Args:
            signals: Signal values from SignalEngineV2
            bias_signals: Bias signal values from BiasSignalEngine
            capital_tier: Current capital tier (S, A, B)

        Returns:
            List of active strategies sorted by confidence
        """
        bias_signals = bias_signals or {}
        active = []

        tier_order = {"S": 0, "A": 1, "B": 2}
        current_tier_level = tier_order.get(capital_tier, 0)

        for strategy_id, strategy in self.strategies.items():
            # Check capital tier requirement
            required_tier_level = tier_order.get(strategy.min_capital_tier, 0)
            if current_tier_level < required_tier_level:
                continue

            # Check signal conditions
            matched, total = self._check_conditions(
                strategy.signal_conditions, signals
            )

            # Check bias conditions
            bias_matched, bias_total = self._check_conditions(
                strategy.bias_conditions, bias_signals
            )

            total_matched = matched + bias_matched
            total_conditions = total + bias_total

            if total_conditions == 0:
                continue

            # Strategy is active if >70% of conditions met
            match_ratio = total_matched / total_conditions
            if match_ratio >= 0.7:
                # Determine direction
                direction = self._determine_direction(strategy_id, signals)

                active.append(ActiveStrategy(
                    strategy_id=strategy_id,
                    category=strategy.category,
                    direction=direction,
                    confidence=match_ratio,
                    signals_matched=total_matched,
                    signals_total=total_conditions
                ))

        # Sort by confidence
        active.sort(key=lambda x: x.confidence, reverse=True)
        return active

    def _check_conditions(
        self,
        conditions: Dict[str, Tuple[Optional[float], Optional[float]]],
        values: Dict[str, Any]
    ) -> Tuple[int, int]:
        """Check how many conditions are met"""
        matched = 0
        total = len(conditions)

        for signal_name, (min_val, max_val) in conditions.items():
            value = values.get(signal_name)

            if value is None:
                continue

            try:
                value = float(value)
            except (TypeError, ValueError):
                continue

            # Check bounds
            if min_val is not None and value < min_val:
                continue
            if max_val is not None and value > max_val:
                continue

            matched += 1

        return matched, total

    def _determine_direction(
        self,
        strategy_id: str,
        signals: Dict[str, Any]
    ) -> Direction:
        """Determine trade direction for a strategy"""
        # Direction based on strategy naming convention
        if "_SHORT" in strategy_id:
            return Direction.SHORT

        # Direction based on signals
        if "FADE" in strategy_id or "MR_" in strategy_id:
            # Mean reversion/fade: opposite of current move
            vwap_z = signals.get("vwap_z", 0)
            if vwap_z and vwap_z < -0.5:
                return Direction.LONG
            elif vwap_z and vwap_z > 0.5:
                return Direction.SHORT

        if "MO_" in strategy_id or "BO_" in strategy_id:
            # Momentum/breakout: with the move
            trend = signals.get("hhll_trend_strength", 0)
            if trend and trend > 0.3:
                return Direction.LONG
            elif trend and trend < -0.3:
                return Direction.SHORT

        return Direction.NEUTRAL

    def detect_conflicts(
        self,
        active_strategies: List[ActiveStrategy]
    ) -> Tuple[bool, List[Tuple[str, str]]]:
        """
        Detect conflicts between active strategies.

        Returns:
            Tuple of (conflict_detected, list of conflicting pairs)
        """
        conflicts = []

        for i, strat_a in enumerate(active_strategies):
            for strat_b in active_strategies[i+1:]:
                # Category conflict
                if self._categories_conflict(strat_a.category, strat_b.category):
                    conflicts.append((strat_a.strategy_id, strat_b.strategy_id))
                    continue

                # Direction conflict (same category, opposite direction)
                if (strat_a.category == strat_b.category and
                    strat_a.direction != Direction.NEUTRAL and
                    strat_b.direction != Direction.NEUTRAL and
                    strat_a.direction != strat_b.direction):
                    conflicts.append((strat_a.strategy_id, strat_b.strategy_id))

        return len(conflicts) > 0, conflicts

    def _categories_conflict(
        self,
        cat_a: StrategyCategory,
        cat_b: StrategyCategory
    ) -> bool:
        """Check if two categories conflict"""
        return ((cat_a, cat_b) in self._conflict_pairs or
                (cat_b, cat_a) in self._conflict_pairs)

    def detect_confluence(
        self,
        active_strategies: List[ActiveStrategy]
    ) -> Tuple[int, List[str]]:
        """
        Detect confluence (multiple strategies agreeing).

        Returns:
            Tuple of (confluence_count, list of agreeing strategy IDs)
        """
        if len(active_strategies) < 2:
            return 0, []

        # Group by direction
        direction_groups: Dict[Direction, List[str]] = {}
        for strat in active_strategies:
            if strat.direction != Direction.NEUTRAL:
                if strat.direction not in direction_groups:
                    direction_groups[strat.direction] = []
                direction_groups[strat.direction].append(strat.strategy_id)

        # Find largest confluence
        max_confluence = 0
        confluence_strategies = []

        for direction, strategies in direction_groups.items():
            if len(strategies) > max_confluence:
                max_confluence = len(strategies)
                confluence_strategies = strategies

        return max_confluence, confluence_strategies

    def compute_strategy_state(
        self,
        signals: Dict[str, Any],
        bias_signals: Optional[Dict[str, float]] = None,
        capital_tier: str = "S"
    ) -> StrategyState:
        """
        Compute full strategy state for the current bar.

        Args:
            signals: Signal values
            bias_signals: Bias signal values
            capital_tier: Current capital tier

        Returns:
            StrategyState with all detection results
        """
        # Detect active strategies
        active = self.detect_active_strategies(signals, bias_signals, capital_tier)

        # Detect conflicts
        conflict_detected, conflict_pairs = self.detect_conflicts(active)

        # Detect confluence
        confluence_count, confluence_strategies = self.detect_confluence(active)

        # Determine dominant category and direction
        dominant_category = None
        dominant_direction = Direction.NEUTRAL

        if active:
            # Most confident strategy's category is dominant
            dominant_category = active[0].category
            dominant_direction = active[0].direction

        # Compute crowding score (how obvious is this setup?)
        crowding_score = self._compute_crowding_score(active, confluence_count)

        # Is dominant strategy counter-trend?
        is_counter_trend = self._is_counter_trend(dominant_direction, signals)

        return StrategyState(
            active_strategies=active,
            conflict_detected=conflict_detected,
            conflict_pairs=conflict_pairs,
            confluence_count=confluence_count,
            confluence_strategies=confluence_strategies,
            dominant_category=dominant_category,
            dominant_direction=dominant_direction,
            crowding_score=crowding_score,
            is_counter_trend=is_counter_trend
        )

    def _compute_crowding_score(
        self,
        active: List[ActiveStrategy],
        confluence_count: int
    ) -> float:
        """Compute how crowded/obvious the trade is"""
        if not active:
            return 0.0

        # High confluence = crowded
        confluence_factor = min(1.0, confluence_count / 3.0)

        # High confidence across many strategies = crowded
        avg_confidence = sum(s.confidence for s in active) / len(active)

        # Many active strategies = crowded
        count_factor = min(1.0, len(active) / 5.0)

        crowding = (confluence_factor * 0.4 +
                   avg_confidence * 0.3 +
                   count_factor * 0.3)

        return min(1.0, crowding)

    def _is_counter_trend(
        self,
        direction: Direction,
        signals: Dict[str, Any]
    ) -> bool:
        """Check if direction is counter-trend"""
        if direction == Direction.NEUTRAL:
            return False

        trend = signals.get("hhll_trend_strength", 0)
        if trend is None:
            return False

        # Counter-trend if direction opposes trend
        if direction == Direction.LONG and trend < -0.3:
            return True
        if direction == Direction.SHORT and trend > 0.3:
            return True

        return False

    def get_strategy_state_dict(self, state: StrategyState) -> Dict[str, Any]:
        """Convert StrategyState to dict for modifier registry"""
        return {
            "conflict_detected": state.conflict_detected,
            "confluence_count": state.confluence_count,
            "crowding_score": state.crowding_score,
            "is_counter_trend": state.is_counter_trend,
            "direction": state.dominant_direction.value if state.dominant_direction else 0,
            "active_count": len(state.active_strategies),
            "dominant_category": state.dominant_category.value if state.dominant_category else None,
        }
