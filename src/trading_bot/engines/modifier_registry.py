"""
Modifier Registry - Context-Based Threshold Adjustments

Modifiers adjust the decision threshold (θ) based on:
1. Time context (time of day, day of week)
2. Event context (pre/post FOMC, expiry days)
3. Regime context (high/low volatility, trending/ranging)
4. Psychological context (bias signals)
5. Strategy context (conflicts, crowding)

θ_effective = θ_base + Σ(active_modifiers)

Higher θ = harder to enter = more conservative
Lower θ = easier to enter = more aggressive
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Dict, List, Optional, Callable, Any, Tuple
from decimal import Decimal
from enum import Enum
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


class ModifierCategory(Enum):
    """Categories of modifiers"""
    TIME = "time"
    EVENT = "event"
    REGIME = "regime"
    PSYCHOLOGICAL = "psychological"
    STRATEGY = "strategy"
    QUALITY = "quality"


@dataclass
class Modifier:
    """A single threshold modifier"""
    id: str
    category: ModifierCategory
    description: str
    adjustment: float  # Added to θ (positive = conservative, negative = aggressive)
    condition: Callable[..., bool]  # Function that returns True if modifier is active
    priority: int = 0  # Higher priority modifiers evaluated first
    stackable: bool = True  # Can stack with other modifiers in same category
    max_per_category: Optional[float] = None  # Cap on total adjustment from this category


@dataclass
class ModifierResult:
    """Result of modifier evaluation"""
    active_modifiers: List[str]
    total_adjustment: float
    adjustments_by_category: Dict[str, float]
    details: Dict[str, Any]


class ModifierRegistry:
    """
    Central registry for all threshold modifiers.

    Modifiers are context-aware adjustments that make it harder or
    easier to enter trades based on current market conditions.
    """

    def __init__(self, base_threshold: float = 0.0):
        self.base_threshold = base_threshold
        self.modifiers: Dict[str, Modifier] = {}
        self._category_caps: Dict[ModifierCategory, float] = {
            ModifierCategory.TIME: 0.15,
            ModifierCategory.EVENT: 0.25,
            ModifierCategory.REGIME: 0.20,
            ModifierCategory.PSYCHOLOGICAL: 0.15,
            ModifierCategory.STRATEGY: 0.20,
            ModifierCategory.QUALITY: 0.30,
        }

        # Register all built-in modifiers
        self._register_time_modifiers()
        self._register_event_modifiers()
        self._register_regime_modifiers()
        self._register_psychological_modifiers()
        self._register_strategy_modifiers()
        self._register_quality_modifiers()

    def register(self, modifier: Modifier):
        """Register a modifier"""
        self.modifiers[modifier.id] = modifier

    def unregister(self, modifier_id: str):
        """Unregister a modifier"""
        if modifier_id in self.modifiers:
            del self.modifiers[modifier_id]

    def evaluate(
        self,
        timestamp: datetime,
        signals: Dict[str, Any],
        bias_signals: Optional[Dict[str, float]] = None,
        strategy_state: Optional[Dict[str, Any]] = None,
        regime_state: Optional[Dict[str, Any]] = None
    ) -> ModifierResult:
        """
        Evaluate all modifiers and compute total adjustment.

        Args:
            timestamp: Current timestamp
            signals: Signal values from SignalEngineV2
            bias_signals: Bias signal values from BiasSignalEngine
            strategy_state: Strategy detection state
            regime_state: Market regime state

        Returns:
            ModifierResult with active modifiers and adjustments
        """
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=ET)

        context = {
            "timestamp": timestamp,
            "signals": signals or {},
            "bias_signals": bias_signals or {},
            "strategy_state": strategy_state or {},
            "regime_state": regime_state or {},
        }

        active_modifiers = []
        adjustments_by_category: Dict[str, float] = {}
        details = {}

        # Sort modifiers by priority
        sorted_modifiers = sorted(
            self.modifiers.values(),
            key=lambda m: m.priority,
            reverse=True
        )

        for modifier in sorted_modifiers:
            try:
                is_active = modifier.condition(**context)
            except Exception:
                is_active = False

            if is_active:
                category_key = modifier.category.value

                # Check category cap
                current_category_adj = adjustments_by_category.get(category_key, 0.0)
                category_cap = self._category_caps.get(modifier.category, 1.0)

                if not modifier.stackable:
                    # Non-stackable: only apply if nothing in category yet
                    if current_category_adj != 0.0:
                        continue

                # Apply adjustment with cap
                new_adj = current_category_adj + modifier.adjustment
                if abs(new_adj) > category_cap:
                    # Cap the adjustment
                    new_adj = category_cap if new_adj > 0 else -category_cap

                adjustments_by_category[category_key] = new_adj
                active_modifiers.append(modifier.id)
                details[modifier.id] = {
                    "description": modifier.description,
                    "adjustment": modifier.adjustment,
                    "category": category_key,
                }

        total_adjustment = sum(adjustments_by_category.values())

        return ModifierResult(
            active_modifiers=active_modifiers,
            total_adjustment=total_adjustment,
            adjustments_by_category=adjustments_by_category,
            details=details
        )

    def get_effective_threshold(
        self,
        timestamp: datetime,
        signals: Dict[str, Any],
        bias_signals: Optional[Dict[str, float]] = None,
        strategy_state: Optional[Dict[str, Any]] = None,
        regime_state: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, ModifierResult]:
        """
        Get effective threshold after all modifiers.

        Returns:
            Tuple of (effective_threshold, modifier_result)
        """
        result = self.evaluate(
            timestamp, signals, bias_signals, strategy_state, regime_state
        )
        effective = self.base_threshold + result.total_adjustment
        return effective, result

    # ==================== TIME MODIFIERS ====================

    def _register_time_modifiers(self):
        """Register time-of-day and day-of-week modifiers"""

        # Opening volatility (09:30-09:35) - BE VERY CAREFUL
        self.register(Modifier(
            id="TIME_OPENING_5MIN",
            category=ModifierCategory.TIME,
            description="First 5 minutes: high volatility, skip",
            adjustment=0.50,  # Very conservative
            condition=lambda timestamp, **_: (
                time(9, 30) <= timestamp.time() < time(9, 35)
            ),
            priority=100
        ))

        # Opening transition (09:35-10:00) - Moderate caution
        self.register(Modifier(
            id="TIME_OPENING_TRANSITION",
            category=ModifierCategory.TIME,
            description="Opening transition: elevated caution",
            adjustment=0.10,
            condition=lambda timestamp, **_: (
                time(9, 35) <= timestamp.time() < time(10, 0)
            ),
            priority=90
        ))

        # Mid-morning sweet spot (10:30-11:30) - Favorable
        self.register(Modifier(
            id="TIME_MID_MORNING",
            category=ModifierCategory.TIME,
            description="Mid-morning: historically favorable",
            adjustment=-0.05,  # Slightly aggressive
            condition=lambda timestamp, **_: (
                time(10, 30) <= timestamp.time() < time(11, 30)
            ),
            priority=80
        ))

        # Lunch doldrums (11:30-13:30) - Already blocked by session, but add modifier
        self.register(Modifier(
            id="TIME_LUNCH",
            category=ModifierCategory.TIME,
            description="Lunch period: low liquidity",
            adjustment=0.25,
            condition=lambda timestamp, **_: (
                time(11, 30) <= timestamp.time() < time(13, 30)
            ),
            priority=95
        ))

        # Afternoon resumption (13:30-14:30) - Moderate
        self.register(Modifier(
            id="TIME_AFTERNOON_EARLY",
            category=ModifierCategory.TIME,
            description="Early afternoon: moderate conditions",
            adjustment=0.0,  # Neutral
            condition=lambda timestamp, **_: (
                time(13, 30) <= timestamp.time() < time(14, 30)
            ),
            priority=70
        ))

        # Power hour (14:30-15:30) - Can be good but volatile
        self.register(Modifier(
            id="TIME_POWER_HOUR",
            category=ModifierCategory.TIME,
            description="Power hour: elevated volatility",
            adjustment=0.05,
            condition=lambda timestamp, **_: (
                time(14, 30) <= timestamp.time() < time(15, 30)
            ),
            priority=75
        ))

        # Close approach (15:30-15:55) - Increasing caution
        self.register(Modifier(
            id="TIME_CLOSE_APPROACH",
            category=ModifierCategory.TIME,
            description="Approaching close: position squaring",
            adjustment=0.15,
            condition=lambda timestamp, **_: (
                time(15, 30) <= timestamp.time() < time(15, 55)
            ),
            priority=85
        ))

        # Friday afternoon - Position squaring
        self.register(Modifier(
            id="DAY_FRIDAY_AFTERNOON",
            category=ModifierCategory.TIME,
            description="Friday afternoon: weekend risk",
            adjustment=0.10,
            condition=lambda timestamp, **_: (
                timestamp.weekday() == 4 and timestamp.time() >= time(14, 0)
            ),
            priority=80
        ))

        # Monday morning - Gap risk residual
        self.register(Modifier(
            id="DAY_MONDAY_MORNING",
            category=ModifierCategory.TIME,
            description="Monday morning: gap effects",
            adjustment=0.05,
            condition=lambda timestamp, **_: (
                timestamp.weekday() == 0 and timestamp.time() < time(11, 0)
            ),
            priority=70
        ))

    # ==================== EVENT MODIFIERS ====================

    def _register_event_modifiers(self):
        """Register event-related modifiers"""

        # Pre-FOMC (Wednesday before 14:00 on FOMC weeks)
        # Simplified: every Wednesday
        self.register(Modifier(
            id="EVENT_PRE_FOMC",
            category=ModifierCategory.EVENT,
            description="Pre-FOMC: uncertainty elevated",
            adjustment=0.20,
            condition=lambda timestamp, **_: (
                timestamp.weekday() == 2 and  # Wednesday
                time(12, 0) <= timestamp.time() < time(14, 0)
            ),
            priority=100
        ))

        # Post-FOMC (Wednesday after 14:30)
        self.register(Modifier(
            id="EVENT_POST_FOMC_IMMEDIATE",
            category=ModifierCategory.EVENT,
            description="Post-FOMC immediate: extreme volatility",
            adjustment=0.25,
            condition=lambda timestamp, **_: (
                timestamp.weekday() == 2 and
                time(14, 0) <= timestamp.time() < time(14, 30)
            ),
            priority=100
        ))

        # Monthly options expiry (3rd Friday)
        self.register(Modifier(
            id="EVENT_MONTHLY_EXPIRY",
            category=ModifierCategory.EVENT,
            description="Monthly expiry: gamma effects",
            adjustment=0.10,
            condition=lambda timestamp, **_: (
                timestamp.weekday() == 4 and
                15 <= timestamp.day <= 21
            ),
            priority=80
        ))

        # Quarter end
        self.register(Modifier(
            id="EVENT_QUARTER_END",
            category=ModifierCategory.EVENT,
            description="Quarter end: rebalancing flows",
            adjustment=0.10,
            condition=lambda timestamp, **_: (
                timestamp.month in [3, 6, 9, 12] and
                timestamp.day >= 25
            ),
            priority=70
        ))

        # Month end
        self.register(Modifier(
            id="EVENT_MONTH_END",
            category=ModifierCategory.EVENT,
            description="Month end: rebalancing flows",
            adjustment=0.05,
            condition=lambda timestamp, **_: (
                timestamp.day >= 28
            ),
            priority=60
        ))

    # ==================== REGIME MODIFIERS ====================

    def _register_regime_modifiers(self):
        """Register market regime modifiers"""

        # High volatility regime
        self.register(Modifier(
            id="REGIME_HIGH_VOL",
            category=ModifierCategory.REGIME,
            description="High volatility regime",
            adjustment=0.15,
            condition=lambda signals, regime_state, **_: (
                regime_state.get("vol_regime") == "high" or
                signals.get("atr_14_n", 1.0) > 1.5
            ),
            priority=90
        ))

        # Low volatility regime - Can be favorable for mean reversion
        self.register(Modifier(
            id="REGIME_LOW_VOL",
            category=ModifierCategory.REGIME,
            description="Low volatility: mean reversion favorable",
            adjustment=-0.05,
            condition=lambda signals, regime_state, **_: (
                regime_state.get("vol_regime") == "low" or
                (signals.get("atr_14_n") is not None and signals.get("atr_14_n") < 0.7)
            ),
            priority=70
        ))

        # Strong trend regime - Favor momentum, raise bar for mean reversion
        self.register(Modifier(
            id="REGIME_TRENDING",
            category=ModifierCategory.REGIME,
            description="Trending market: favor momentum",
            adjustment=0.0,  # Neutral overall, but affects template selection
            condition=lambda signals, **_: (
                abs(signals.get("hhll_trend_strength", 0)) > 0.7
            ),
            priority=60
        ))

        # Choppy/ranging regime
        self.register(Modifier(
            id="REGIME_CHOPPY",
            category=ModifierCategory.REGIME,
            description="Choppy market: reduced edge",
            adjustment=0.10,
            condition=lambda signals, **_: (
                signals.get("range_compression") is not None and
                0.8 < signals.get("range_compression", 1.0) < 1.2 and
                abs(signals.get("hhll_trend_strength", 0)) < 0.3
            ),
            priority=65
        ))

        # Wide spread regime
        self.register(Modifier(
            id="REGIME_WIDE_SPREAD",
            category=ModifierCategory.REGIME,
            description="Wide spreads: execution risk",
            adjustment=0.15,
            condition=lambda signals, **_: (
                signals.get("spread_proxy_tickiness") is not None and
                signals.get("spread_proxy_tickiness") < 0.5
            ),
            priority=85
        ))

    # ==================== PSYCHOLOGICAL MODIFIERS ====================

    def _register_psychological_modifiers(self):
        """Register psychological/bias modifiers"""

        # High FOMO environment
        self.register(Modifier(
            id="PSYCH_HIGH_FOMO",
            category=ModifierCategory.PSYCHOLOGICAL,
            description="High FOMO: resist chasing",
            adjustment=0.10,
            condition=lambda bias_signals, **_: (
                bias_signals.get("fomo_index", 0) > 0.7
            ),
            priority=80
        ))

        # Panic environment
        self.register(Modifier(
            id="PSYCH_PANIC",
            category=ModifierCategory.PSYCHOLOGICAL,
            description="Panic conditions: wait for stabilization",
            adjustment=0.15,
            condition=lambda bias_signals, **_: (
                bias_signals.get("panic_index", 0) > 0.7
            ),
            priority=85
        ))

        # Euphoria warning
        self.register(Modifier(
            id="PSYCH_EUPHORIA",
            category=ModifierCategory.PSYCHOLOGICAL,
            description="Euphoria: blow-off top risk",
            adjustment=0.20,
            condition=lambda bias_signals, **_: (
                bias_signals.get("euphoria_flag", 0) > 0.6
            ),
            priority=90
        ))

        # Herding detected
        self.register(Modifier(
            id="PSYCH_HERDING",
            category=ModifierCategory.PSYCHOLOGICAL,
            description="Herding: crowded trade risk",
            adjustment=0.08,
            condition=lambda bias_signals, **_: (
                bias_signals.get("herding_score", 0) > 0.6
            ),
            priority=70
        ))

        # Overconfidence after wins
        self.register(Modifier(
            id="PSYCH_OVERCONFIDENCE",
            category=ModifierCategory.PSYCHOLOGICAL,
            description="Overconfidence: winning streak caution",
            adjustment=0.10,
            condition=lambda bias_signals, **_: (
                bias_signals.get("overconfidence_flag", 0) > 0.5
            ),
            priority=75
        ))

        # Good psychological state - All biases low
        self.register(Modifier(
            id="PSYCH_CLEAR",
            category=ModifierCategory.PSYCHOLOGICAL,
            description="Clear psychological state",
            adjustment=-0.05,
            condition=lambda bias_signals, **_: (
                bias_signals.get("psychological_state_score", 0.5) < 0.3
            ),
            priority=60
        ))

    # ==================== STRATEGY MODIFIERS ====================

    def _register_strategy_modifiers(self):
        """Register strategy-related modifiers"""

        # Strategy conflict detected
        self.register(Modifier(
            id="STRATEGY_CONFLICT",
            category=ModifierCategory.STRATEGY,
            description="Conflicting strategies active",
            adjustment=0.15,
            condition=lambda strategy_state, **_: (
                strategy_state.get("conflict_detected", False)
            ),
            priority=90
        ))

        # Multiple strategies agree
        self.register(Modifier(
            id="STRATEGY_CONFLUENCE",
            category=ModifierCategory.STRATEGY,
            description="Strategy confluence: multiple agree",
            adjustment=-0.05,
            condition=lambda strategy_state, **_: (
                strategy_state.get("confluence_count", 0) >= 2
            ),
            priority=80
        ))

        # Crowded strategy warning
        self.register(Modifier(
            id="STRATEGY_CROWDED",
            category=ModifierCategory.STRATEGY,
            description="Crowded strategy: reduced edge",
            adjustment=0.10,
            condition=lambda strategy_state, **_: (
                strategy_state.get("crowding_score", 0) > 0.7
            ),
            priority=75
        ))

        # Counter-trend attempt
        self.register(Modifier(
            id="STRATEGY_COUNTER_TREND",
            category=ModifierCategory.STRATEGY,
            description="Counter-trend: higher bar",
            adjustment=0.10,
            condition=lambda strategy_state, signals, **_: (
                strategy_state.get("is_counter_trend", False) or
                (strategy_state.get("direction") is not None and
                 signals.get("hhll_trend_strength", 0) is not None and
                 (strategy_state.get("direction") * signals.get("hhll_trend_strength", 0)) < -0.3)
            ),
            priority=70
        ))

    # ==================== QUALITY MODIFIERS ====================

    def _register_quality_modifiers(self):
        """Register data/execution quality modifiers"""

        # DVS degraded
        self.register(Modifier(
            id="QUALITY_DVS_LOW",
            category=ModifierCategory.QUALITY,
            description="Data quality degraded",
            adjustment=0.15,
            condition=lambda signals, **_: (
                signals.get("dvs", 1.0) < 0.85
            ),
            priority=90
        ))

        # EQS degraded
        self.register(Modifier(
            id="QUALITY_EQS_LOW",
            category=ModifierCategory.QUALITY,
            description="Execution quality degraded",
            adjustment=0.10,
            condition=lambda signals, **_: (
                signals.get("eqs", 1.0) < 0.80
            ),
            priority=85
        ))

        # Friction regime poor
        self.register(Modifier(
            id="QUALITY_HIGH_FRICTION",
            category=ModifierCategory.QUALITY,
            description="High friction environment",
            adjustment=0.15,
            condition=lambda signals, **_: (
                signals.get("friction_regime_index") is not None and
                signals.get("friction_regime_index") < 0.5
            ),
            priority=80
        ))

        # Excellent conditions
        self.register(Modifier(
            id="QUALITY_EXCELLENT",
            category=ModifierCategory.QUALITY,
            description="Excellent data and execution quality",
            adjustment=-0.05,
            condition=lambda signals, **_: (
                signals.get("dvs", 0) >= 0.95 and
                signals.get("eqs", 0) >= 0.90 and
                (signals.get("friction_regime_index") is None or
                 signals.get("friction_regime_index") >= 0.8)
            ),
            priority=70
        ))


# Convenience function for quick threshold calculation
def get_modified_threshold(
    base_threshold: float,
    timestamp: datetime,
    signals: Dict[str, Any],
    bias_signals: Optional[Dict[str, float]] = None,
    strategy_state: Optional[Dict[str, Any]] = None,
    regime_state: Optional[Dict[str, Any]] = None
) -> Tuple[float, List[str]]:
    """
    Quick function to get modified threshold.

    Returns:
        Tuple of (effective_threshold, list_of_active_modifier_ids)
    """
    registry = ModifierRegistry(base_threshold)
    threshold, result = registry.get_effective_threshold(
        timestamp, signals, bias_signals, strategy_state, regime_state
    )
    return threshold, result.active_modifiers
