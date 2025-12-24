"""
Attribution Engine V3 - Enhanced with Bias/Strategy Tracking

Extends attribution system with:
1. Bias-level attribution (which biases influenced the trade)
2. Strategy-level attribution (which strategy signature was active)
3. Modifier-level attribution (which modifiers affected threshold)
4. Conflict-level attribution (was there strategy conflict)
5. Meta-cognition attribution (was the system overconfident)

Attribution Categories (Extended):
A0: Success (P&L > 0)
A1: Wrong model (constraint failed)
A2: Wrong timing (correct pattern, early/late)
A3: Noise stop (random volatility hit stop)
A4: Wrong expression (template mismatch)
A5: Regime shift (market structure changed)
A6: Event shock (news/unpredictable)
A7: Data quality (DVS/EQS degraded)
A8: Execution failure (broker issue)
A9: Undetermined

NEW CATEGORIES:
A10: Bias misfire (bias signal was wrong)
A11: Strategy conflict ignored (conflict was present, trade failed)
A12: Modifier override (modifiers suggested skip, traded anyway)
A13: Meta-cognition failure (overconfidence, confirmation bias)
A14: Crowded trade (too obvious, got faded)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from decimal import Decimal


class AttributionCategory(Enum):
    """Attribution categories including new bias/strategy categories"""
    A0_SUCCESS = "A0"
    A1_WRONG_MODEL = "A1"
    A2_WRONG_TIMING = "A2"
    A3_NOISE_STOP = "A3"
    A4_WRONG_EXPRESSION = "A4"
    A5_REGIME_SHIFT = "A5"
    A6_EVENT_SHOCK = "A6"
    A7_DATA_QUALITY = "A7"
    A8_EXECUTION_FAILURE = "A8"
    A9_UNDETERMINED = "A9"
    # New categories
    A10_BIAS_MISFIRE = "A10"
    A11_CONFLICT_IGNORED = "A11"
    A12_MODIFIER_OVERRIDE = "A12"
    A13_META_COGNITION_FAILURE = "A13"
    A14_CROWDED_TRADE = "A14"


@dataclass
class TradeSnapshot:
    """Snapshot of state at trade entry"""
    # Core signals at entry
    signals: Dict[str, Any]

    # Bias signals at entry
    bias_signals: Dict[str, float]

    # Strategy state at entry
    strategy_state: Dict[str, Any]

    # Beliefs at entry
    beliefs: Dict[str, float]

    # Modifiers at entry
    active_modifiers: List[str]
    effective_threshold: float

    # Decision metadata
    template_id: str
    constraint_id: str
    direction: int  # 1 = long, -1 = short

    # Risk parameters
    stop_ticks: int
    target_ticks: int

    # Timestamps
    entry_time: datetime
    entry_price: Decimal


@dataclass
class TradeResult:
    """Result of a completed trade"""
    # Entry snapshot
    entry_snapshot: TradeSnapshot

    # Exit data
    exit_time: datetime
    exit_price: Decimal
    exit_reason: str  # "TARGET", "STOP", "TIME", "MANUAL", etc.

    # P&L
    pnl_ticks: int
    pnl_usd: Decimal

    # Signals at exit (for lookforward)
    signals_at_exit: Dict[str, Any]
    bias_signals_at_exit: Dict[str, float]


@dataclass
class AttributionResult:
    """Complete attribution for a trade"""
    # Primary attribution
    primary_category: AttributionCategory
    primary_reason: str

    # Secondary attributions (multiple may apply)
    secondary_categories: List[AttributionCategory]

    # Bias attribution
    bias_contributors: Dict[str, float]  # Which biases contributed to outcome
    bias_misfires: List[str]  # Which bias signals were wrong

    # Strategy attribution
    strategy_at_entry: str
    strategy_was_correct: bool
    conflict_was_present: bool
    conflict_contributed: bool

    # Modifier attribution
    modifiers_at_entry: List[str]
    modifier_override_occurred: bool

    # Meta-cognition attribution
    overconfidence_at_entry: float
    meta_cognition_contributed: bool

    # Crowding attribution
    crowding_at_entry: float
    crowded_trade: bool

    # Process vs Outcome scoring
    process_score: float  # Did we follow the system? [0, 1]
    outcome_score: float  # Did we make money? [0, 1]
    combined_score: float  # 70% process, 30% outcome

    # Lookforward analysis
    lookforward_15_outcome: Optional[str]  # What happened 15 bars later
    lookforward_30_outcome: Optional[str]  # What happened 30 bars later

    # Parameter update suggestions
    suggested_updates: Dict[str, Any]


class AttributionEngineV3:
    """
    Enhanced attribution engine with bias and strategy tracking.

    This engine analyzes completed trades and attributes outcomes to
    specific biases, strategies, and system components.
    """

    def __init__(self):
        # Lookforward windows in bars
        self.lookforward_windows = [15, 30]

        # Attribution classification order (first match wins)
        self.classification_order = [
            AttributionCategory.A8_EXECUTION_FAILURE,
            AttributionCategory.A7_DATA_QUALITY,
            AttributionCategory.A6_EVENT_SHOCK,
            AttributionCategory.A5_REGIME_SHIFT,
            AttributionCategory.A14_CROWDED_TRADE,
            AttributionCategory.A11_CONFLICT_IGNORED,
            AttributionCategory.A13_META_COGNITION_FAILURE,
            AttributionCategory.A10_BIAS_MISFIRE,
            AttributionCategory.A12_MODIFIER_OVERRIDE,
            AttributionCategory.A0_SUCCESS,
            AttributionCategory.A4_WRONG_EXPRESSION,
            AttributionCategory.A2_WRONG_TIMING,
            AttributionCategory.A3_NOISE_STOP,
            AttributionCategory.A1_WRONG_MODEL,
            AttributionCategory.A9_UNDETERMINED,
        ]

        # Bias influence thresholds
        self.bias_thresholds = {
            "fomo_index": 0.7,
            "panic_index": 0.7,
            "euphoria_flag": 0.6,
            "overconfidence_flag": 0.6,
            "herding_score": 0.6,
        }

    def attribute(
        self,
        trade_result: TradeResult,
        lookforward_bars: Optional[List[Dict[str, Any]]] = None
    ) -> AttributionResult:
        """
        Perform complete attribution analysis on a trade.

        Args:
            trade_result: The completed trade with entry/exit data
            lookforward_bars: Bars after exit for lookforward analysis

        Returns:
            AttributionResult with complete attribution
        """
        entry = trade_result.entry_snapshot

        # Compute primary attribution
        primary_cat, primary_reason = self._classify_primary(trade_result)

        # Compute secondary attributions
        secondary_cats = self._classify_secondary(trade_result, primary_cat)

        # Analyze bias contribution
        bias_contributors, bias_misfires = self._analyze_bias_contribution(
            trade_result
        )

        # Analyze strategy contribution
        (strategy_correct, conflict_present,
         conflict_contributed) = self._analyze_strategy_contribution(trade_result)

        # Analyze modifier contribution
        modifier_override = self._analyze_modifier_contribution(trade_result)

        # Analyze meta-cognition
        overconf = entry.bias_signals.get("overconfidence_flag", 0)
        meta_contributed = self._analyze_meta_contribution(trade_result)

        # Analyze crowding
        crowding = entry.strategy_state.get("crowding_score", 0)
        crowded = crowding > 0.7 and trade_result.pnl_ticks < 0

        # Compute scores
        process_score = self._compute_process_score(trade_result)
        outcome_score = self._compute_outcome_score(trade_result)
        combined_score = 0.7 * process_score + 0.3 * outcome_score

        # Lookforward analysis
        lookforward_15, lookforward_30 = self._analyze_lookforward(
            trade_result, lookforward_bars
        )

        # Generate update suggestions
        suggested_updates = self._generate_update_suggestions(
            trade_result, primary_cat, bias_misfires
        )

        return AttributionResult(
            primary_category=primary_cat,
            primary_reason=primary_reason,
            secondary_categories=secondary_cats,
            bias_contributors=bias_contributors,
            bias_misfires=bias_misfires,
            strategy_at_entry=entry.strategy_state.get("dominant_category", "UNKNOWN"),
            strategy_was_correct=strategy_correct,
            conflict_was_present=conflict_present,
            conflict_contributed=conflict_contributed,
            modifiers_at_entry=entry.active_modifiers,
            modifier_override_occurred=modifier_override,
            overconfidence_at_entry=overconf,
            meta_cognition_contributed=meta_contributed,
            crowding_at_entry=crowding,
            crowded_trade=crowded,
            process_score=process_score,
            outcome_score=outcome_score,
            combined_score=combined_score,
            lookforward_15_outcome=lookforward_15,
            lookforward_30_outcome=lookforward_30,
            suggested_updates=suggested_updates,
        )

    def _classify_primary(
        self,
        trade_result: TradeResult
    ) -> tuple[AttributionCategory, str]:
        """Classify primary attribution category"""
        entry = trade_result.entry_snapshot
        pnl = trade_result.pnl_ticks

        # A0: Success
        if pnl > 0:
            return AttributionCategory.A0_SUCCESS, "Trade was profitable"

        # A8: Execution failure (would need broker data)
        # Skip for now

        # A7: Data quality
        if entry.signals.get("dvs", 1.0) < 0.75:
            return AttributionCategory.A7_DATA_QUALITY, "DVS was below threshold at entry"

        # A6: Event shock (would need event calendar)
        # Check for extreme vol spike
        if (trade_result.signals_at_exit.get("atr_14_n") and
            entry.signals.get("atr_14_n") and
            trade_result.signals_at_exit["atr_14_n"] > entry.signals["atr_14_n"] * 1.5):
            return AttributionCategory.A6_EVENT_SHOCK, "Volatility spiked during trade"

        # A5: Regime shift
        entry_trend = entry.signals.get("hhll_trend_strength", 0)
        exit_trend = trade_result.signals_at_exit.get("hhll_trend_strength", 0)
        if entry_trend and exit_trend and entry_trend * exit_trend < -0.2:
            return AttributionCategory.A5_REGIME_SHIFT, "Trend reversed during trade"

        # A14: Crowded trade
        if entry.strategy_state.get("crowding_score", 0) > 0.7:
            return AttributionCategory.A14_CROWDED_TRADE, "Trade was too crowded/obvious"

        # A11: Conflict ignored
        if entry.strategy_state.get("conflict_detected", False):
            return AttributionCategory.A11_CONFLICT_IGNORED, "Strategy conflict was present at entry"

        # A13: Meta-cognition failure
        if entry.bias_signals.get("overconfidence_flag", 0) > 0.6:
            return AttributionCategory.A13_META_COGNITION_FAILURE, "Overconfidence at entry"

        # A10: Bias misfire
        bias_misfires = self._find_bias_misfires(trade_result)
        if bias_misfires:
            return AttributionCategory.A10_BIAS_MISFIRE, f"Bias signals misfired: {', '.join(bias_misfires)}"

        # A4: Wrong expression
        if trade_result.exit_reason == "STOP":
            entry_belief = entry.beliefs.get(entry.constraint_id, 0)
            if entry_belief < 0.6:
                return AttributionCategory.A4_WRONG_EXPRESSION, "Template didn't match constraint"

        # A2: Wrong timing
        # Check if pattern played out after stop
        if trade_result.exit_reason == "STOP":
            # Would need lookforward data
            return AttributionCategory.A2_WRONG_TIMING, "Pattern was correct but timing was off"

        # A3: Noise stop
        if trade_result.exit_reason == "STOP" and abs(pnl) <= 4:
            return AttributionCategory.A3_NOISE_STOP, "Stop hit by normal volatility"

        # A1: Wrong model
        if pnl < 0:
            return AttributionCategory.A1_WRONG_MODEL, "Constraint model was incorrect"

        return AttributionCategory.A9_UNDETERMINED, "Could not determine attribution"

    def _classify_secondary(
        self,
        trade_result: TradeResult,
        primary: AttributionCategory
    ) -> List[AttributionCategory]:
        """Find secondary attributions that also apply"""
        secondary = []
        entry = trade_result.entry_snapshot

        if primary != AttributionCategory.A11_CONFLICT_IGNORED:
            if entry.strategy_state.get("conflict_detected", False):
                secondary.append(AttributionCategory.A11_CONFLICT_IGNORED)

        if primary != AttributionCategory.A13_META_COGNITION_FAILURE:
            if entry.bias_signals.get("overconfidence_flag", 0) > 0.5:
                secondary.append(AttributionCategory.A13_META_COGNITION_FAILURE)

        if primary != AttributionCategory.A14_CROWDED_TRADE:
            if entry.strategy_state.get("crowding_score", 0) > 0.6:
                secondary.append(AttributionCategory.A14_CROWDED_TRADE)

        return secondary

    def _analyze_bias_contribution(
        self,
        trade_result: TradeResult
    ) -> tuple[Dict[str, float], List[str]]:
        """Analyze which biases contributed to outcome"""
        entry = trade_result.entry_snapshot
        contributors = {}
        misfires = []

        was_profitable = trade_result.pnl_ticks > 0

        for bias_name, threshold in self.bias_thresholds.items():
            value = entry.bias_signals.get(bias_name, 0)

            if value > threshold:
                # Bias was elevated at entry
                contributors[bias_name] = value

                if not was_profitable:
                    # Elevated bias + loss = potential misfire
                    misfires.append(bias_name)

        return contributors, misfires

    def _find_bias_misfires(self, trade_result: TradeResult) -> List[str]:
        """Find bias signals that gave wrong indication"""
        _, misfires = self._analyze_bias_contribution(trade_result)
        return misfires

    def _analyze_strategy_contribution(
        self,
        trade_result: TradeResult
    ) -> tuple[bool, bool, bool]:
        """Analyze strategy contribution to outcome"""
        entry = trade_result.entry_snapshot
        was_profitable = trade_result.pnl_ticks > 0

        strategy_correct = was_profitable
        conflict_present = entry.strategy_state.get("conflict_detected", False)
        conflict_contributed = conflict_present and not was_profitable

        return strategy_correct, conflict_present, conflict_contributed

    def _analyze_modifier_contribution(
        self,
        trade_result: TradeResult
    ) -> bool:
        """Check if modifiers suggested skip but we traded anyway"""
        entry = trade_result.entry_snapshot

        # If threshold was raised significantly and we still traded
        if entry.effective_threshold > 0.1 and trade_result.pnl_ticks < 0:
            return True

        return False

    def _analyze_meta_contribution(
        self,
        trade_result: TradeResult
    ) -> bool:
        """Check if meta-cognition issues contributed to loss"""
        entry = trade_result.entry_snapshot

        if trade_result.pnl_ticks >= 0:
            return False

        overconf = entry.bias_signals.get("overconfidence_flag", 0)
        confirm = entry.bias_signals.get("confirmation_bias_risk", 0)
        hindsight = entry.bias_signals.get("hindsight_trap_flag", 0)

        return overconf > 0.5 or confirm > 0.5 or hindsight > 0.5

    def _compute_process_score(self, trade_result: TradeResult) -> float:
        """Compute process quality score [0, 1]"""
        entry = trade_result.entry_snapshot
        score = 1.0
        penalties = []

        # Penalty for low DVS
        if entry.signals.get("dvs", 1.0) < 0.85:
            score -= 0.1
            penalties.append("low_dvs")

        # Penalty for strategy conflict
        if entry.strategy_state.get("conflict_detected", False):
            score -= 0.15
            penalties.append("conflict")

        # Penalty for overconfidence
        if entry.bias_signals.get("overconfidence_flag", 0) > 0.6:
            score -= 0.1
            penalties.append("overconfidence")

        # Penalty for crowding
        if entry.strategy_state.get("crowding_score", 0) > 0.7:
            score -= 0.1
            penalties.append("crowded")

        # Penalty for high threshold override
        if entry.effective_threshold > 0.15:
            score -= 0.1
            penalties.append("threshold_override")

        # Bonus for confluence
        if entry.strategy_state.get("confluence_count", 0) >= 2:
            score += 0.05

        return max(0.0, min(1.0, score))

    def _compute_outcome_score(self, trade_result: TradeResult) -> float:
        """Compute outcome score [0, 1]"""
        pnl = trade_result.pnl_ticks

        if pnl >= 8:  # Full target
            return 1.0
        elif pnl >= 4:  # Partial win
            return 0.8
        elif pnl >= 0:  # Breakeven
            return 0.5
        elif pnl >= -4:  # Small loss
            return 0.3
        else:  # Full stop
            return 0.0

    def _analyze_lookforward(
        self,
        trade_result: TradeResult,
        lookforward_bars: Optional[List[Dict[str, Any]]]
    ) -> tuple[Optional[str], Optional[str]]:
        """Analyze what happened after exit"""
        if not lookforward_bars:
            return None, None

        entry = trade_result.entry_snapshot
        exit_price = float(trade_result.exit_price)
        direction = entry.direction

        lookforward_15 = None
        lookforward_30 = None

        # Check 15 bars
        if len(lookforward_bars) >= 15:
            bar_15 = lookforward_bars[14]
            price_15 = bar_15.get("close", exit_price)
            move_15 = (price_15 - exit_price) * direction

            if move_15 > 2:  # 2+ points in our direction
                lookforward_15 = "WOULD_HAVE_WORKED"
            elif move_15 < -2:
                lookforward_15 = "CORRECT_EXIT"
            else:
                lookforward_15 = "NEUTRAL"

        # Check 30 bars
        if len(lookforward_bars) >= 30:
            bar_30 = lookforward_bars[29]
            price_30 = bar_30.get("close", exit_price)
            move_30 = (price_30 - exit_price) * direction

            if move_30 > 4:
                lookforward_30 = "WOULD_HAVE_WORKED"
            elif move_30 < -4:
                lookforward_30 = "CORRECT_EXIT"
            else:
                lookforward_30 = "NEUTRAL"

        return lookforward_15, lookforward_30

    def _generate_update_suggestions(
        self,
        trade_result: TradeResult,
        primary_cat: AttributionCategory,
        bias_misfires: List[str]
    ) -> Dict[str, Any]:
        """Generate parameter update suggestions based on attribution"""
        suggestions = {}

        # Bias weight adjustments
        if bias_misfires:
            suggestions["bias_weight_adjustments"] = {
                bias: -0.02 for bias in bias_misfires  # Reduce weight
            }

        # Threshold adjustments
        if primary_cat == AttributionCategory.A11_CONFLICT_IGNORED:
            suggestions["conflict_penalty_increase"] = 0.02

        if primary_cat == AttributionCategory.A14_CROWDED_TRADE:
            suggestions["crowding_threshold_decrease"] = 0.05

        if primary_cat == AttributionCategory.A13_META_COGNITION_FAILURE:
            suggestions["overconfidence_gate_decrease"] = 0.05

        # Template adjustments
        if primary_cat == AttributionCategory.A4_WRONG_EXPRESSION:
            entry = trade_result.entry_snapshot
            suggestions["template_review"] = entry.template_id

        return suggestions


# Factory function
def create_attribution_engine() -> AttributionEngineV3:
    """Create enhanced attribution engine"""
    return AttributionEngineV3()
