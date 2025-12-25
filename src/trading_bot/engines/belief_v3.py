"""
Belief Engine V3 - Enhanced with Bias Signals and Strategy Context

Extends BeliefEngineV2 with:
1. Integration of 22 bias-derived signals (S29-S50)
2. Strategy context influence on constraint likelihoods
3. Expanded constraint-signal matrix
4. Conflict-aware likelihood adjustments
5. Meta-cognition gating

This is the "complete understanding" version that incorporates
all 150 biases and 150 strategies through their signal representations.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from decimal import Decimal
import math

from .belief_v2 import BeliefEngineV2, ConstraintLikelihood


@dataclass
class EnhancedConstraintLikelihood(ConstraintLikelihood):
    """Extended likelihood with bias and strategy context"""
    bias_adjustment: float  # Adjustment from bias signals
    strategy_adjustment: float  # Adjustment from strategy context
    conflict_penalty: float  # Penalty from strategy conflicts
    meta_cognition_gate: float  # Gate from meta-cognition signals
    raw_likelihood: float  # Likelihood before adjustments
    final_likelihood: float  # Likelihood after all adjustments


class BeliefEngineV3(BeliefEngineV2):
    """
    Enhanced belief engine incorporating bias signals and strategy context.

    The 300 biases/strategies are integrated as:
    1. Additional signals in the constraint-signal matrix (bias signals)
    2. Likelihood modifiers based on psychological state
    3. Conflict penalties when strategies disagree
    4. Meta-cognition gates that reduce overconfidence
    """

    def __init__(self):
        super().__init__()

        # Extended constraint-signal matrix with bias signals
        self.extended_matrix = self._build_extended_matrix()

        # Bias signal weights per constraint
        self.bias_weights = self._build_bias_weights()

        # Strategy context influence
        self.strategy_influence = {
            "F1": {"preferred_categories": ["MR", "ST"], "conflict_penalty": 0.15},
            "F3": {"preferred_categories": ["FA", "ST"], "conflict_penalty": 0.12},
            "F4": {"preferred_categories": ["FA", "SC"], "conflict_penalty": 0.10},
            "F5": {"preferred_categories": ["MO", "BO"], "conflict_penalty": 0.10},
            "F6": {"preferred_categories": [], "conflict_penalty": 0.05},
        }

        # Meta-cognition thresholds
        self.meta_thresholds = {
            "overconfidence_gate": 0.7,  # Reduce likelihood if overconfident
            "confirmation_bias_gate": 0.6,  # Reduce if confirmation bias risk
            "hindsight_trap_gate": 0.5,  # Reduce if hindsight trap detected
        }

    def _build_extended_matrix(self) -> Dict[str, Dict[str, float]]:
        """
        Build extended constraint-signal matrix including bias signals.

        This expands the original matrix with bias-derived signals.
        """
        return {
            # F1 (K1): VWAP Mean Reversion - Enhanced
            "F1": {
                # Original signals
                "vwap_z": 0.30,
                "range_compression": 0.15,
                "vol_z": -0.10,
                "close_location_value": 0.10,
                "friction_regime_index": 0.08,
                # Bias signals
                "fomo_index": -0.08,  # High FOMO = bad for MR
                "panic_index": 0.05,  # Panic can create MR opportunity
                "herding_score": -0.06,  # Herding = bad for MR
                "round_number_proximity": 0.06,  # Round numbers support MR
                "anchoring_level_distance": 0.05,  # Near anchors = MR works
                "time_of_day_edge": 0.04,  # Time edge matters
                "overconfidence_flag": -0.03,  # Reduce if overconfident
            },

            # F3 (K2): Failed Break Fade - Enhanced
            "F3": {
                # Original signals
                "breakout_distance_n": 0.25,
                "rejection_wick_n": 0.25,
                "vol_z": 0.15,
                "hhll_trend_strength": -0.08,
                "opening_range_break": 0.07,
                # Bias signals
                "fomo_index": 0.05,  # FOMO creates failed breaks
                "herding_score": 0.05,  # Herding creates traps
                "greed_index": 0.04,  # Greed creates extensions to fade
                "opening_drive_exhaustion": 0.06,  # Exhaustion = fade opportunity
            },

            # F4 (K3): Sweep Reversal - Enhanced
            "F4": {
                # Original signals
                "rejection_wick_n": 0.28,
                "climax_bar_flag": 0.20,
                "micro_trend_5": -0.12,
                "close_location_value": 0.12,
                "distance_from_poc_proxy": 0.08,
                # Bias signals
                "panic_index": 0.06,  # Panic creates sweep opportunities
                "euphoria_flag": 0.05,  # Euphoria creates reversals
                "round_number_proximity": 0.05,  # Sweeps happen at round numbers
                "gamma_exposure_proxy": 0.04,  # Gamma can cause sweeps
            },

            # F5 (K4): Momentum Continuation - Enhanced
            "F5": {
                # Original signals
                "hhll_trend_strength": 0.25,
                "micro_trend_5": 0.20,
                "real_body_impulse_n": 0.15,
                "range_expansion_on_volume": 0.12,
                "participation_expansion_index": 0.08,
                # Bias signals
                "fomo_index": -0.05,  # Don't chase FOMO
                "herding_score": -0.04,  # Late to herding = bad
                "recency_bias_score": -0.04,  # Recency bias = dangerous
                "time_of_day_edge": 0.05,  # Time edge matters
                "day_of_week_edge": 0.04,  # Day edge matters
            },

            # F6: Noise Filter - Enhanced with all quality signals
            "F6": {
                # Original signals
                "dvs": 0.30,
                "friction_regime_index": 0.20,
                "lunch_void_gate": 0.12,
                "spread_proxy_tickiness": 0.08,
                "slippage_risk_proxy": 0.05,
                # Bias signals
                "psychological_state_score": -0.10,  # Poor psych = noise
                "meta_cognition_score": -0.08,  # Poor meta = noise
                "temporal_bias_score": 0.07,  # Good temporal = less noise
            },
        }

    def _build_bias_weights(self) -> Dict[str, Dict[str, float]]:
        """
        Build bias signal weight matrix per constraint.

        These weights adjust likelihood based on psychological/structural biases.
        """
        return {
            "F1": {
                "psychological_state_score": -0.15,  # Poor psych hurts MR
                "structural_bias_score": 0.10,  # Structure helps MR
                "temporal_bias_score": 0.10,  # Good timing helps MR
                "meta_cognition_score": -0.10,  # Poor meta hurts MR
            },
            "F3": {
                "psychological_state_score": 0.05,  # FOMO helps failed breaks
                "structural_bias_score": 0.12,  # Structure helps fades
                "temporal_bias_score": 0.08,
                "meta_cognition_score": -0.08,
            },
            "F4": {
                "psychological_state_score": 0.10,  # Panic helps sweeps
                "structural_bias_score": 0.10,
                "temporal_bias_score": 0.05,
                "meta_cognition_score": -0.10,
            },
            "F5": {
                "psychological_state_score": -0.10,  # Poor psych hurts momentum
                "structural_bias_score": -0.05,  # Structure can trap momentum
                "temporal_bias_score": 0.12,  # Timing crucial for momentum
                "meta_cognition_score": -0.12,  # Overconfidence kills momentum
            },
            "F6": {
                "psychological_state_score": -0.20,
                "structural_bias_score": 0.05,
                "temporal_bias_score": 0.15,
                "meta_cognition_score": -0.15,
            },
        }

    def compute_extended_evidence(
        self,
        constraint_id: str,
        signals: Dict[str, Any],
        bias_signals: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Compute evidence using extended matrix with bias signals.
        """
        if constraint_id not in self.extended_matrix:
            return self.compute_evidence(constraint_id, signals)

        weights = self.extended_matrix[constraint_id]
        combined_signals = dict(signals)

        # Add bias signals
        if bias_signals:
            combined_signals.update(bias_signals)

        evidence = 0.0
        total_abs_weight = 0.0

        for signal_name, weight in weights.items():
            signal_value = combined_signals.get(signal_name)

            if signal_value is None:
                continue

            try:
                if isinstance(signal_value, (Decimal, int)):
                    signal_value = float(signal_value)
                else:
                    signal_value = float(signal_value)
            except (TypeError, ValueError):
                continue

            evidence += weight * signal_value
            total_abs_weight += abs(weight)

        if total_abs_weight > 0:
            evidence /= total_abs_weight

        return evidence

    def compute_bias_adjustment(
        self,
        constraint_id: str,
        bias_signals: Dict[str, float]
    ) -> float:
        """
        Compute likelihood adjustment from bias signals.

        Returns adjustment in [-0.2, 0.2] range.
        """
        if constraint_id not in self.bias_weights:
            return 0.0

        weights = self.bias_weights[constraint_id]
        adjustment = 0.0

        for signal_name, weight in weights.items():
            value = bias_signals.get(signal_name, 0.5)  # Default neutral
            # Center around 0.5
            centered = value - 0.5
            adjustment += weight * centered

        # Clamp adjustment
        return max(-0.20, min(0.20, adjustment))

    def compute_strategy_adjustment(
        self,
        constraint_id: str,
        strategy_state: Dict[str, Any]
    ) -> float:
        """
        Compute likelihood adjustment from strategy context.

        Positive when strategy aligns with constraint.
        Negative when strategies conflict.
        """
        if constraint_id not in self.strategy_influence:
            return 0.0

        influence = self.strategy_influence[constraint_id]
        preferred = influence["preferred_categories"]

        # Check if dominant strategy category aligns
        dominant_cat = strategy_state.get("dominant_category")
        alignment_bonus = 0.0

        if dominant_cat and dominant_cat in preferred:
            alignment_bonus = 0.05

        # Confluence bonus
        confluence = strategy_state.get("confluence_count", 0)
        if confluence >= 2:
            alignment_bonus += 0.03

        return alignment_bonus

    def compute_conflict_penalty(
        self,
        constraint_id: str,
        strategy_state: Dict[str, Any]
    ) -> float:
        """
        Compute penalty when strategies conflict.

        Returns penalty in [0, 0.2] range (always reduces likelihood).
        """
        if not strategy_state.get("conflict_detected", False):
            return 0.0

        if constraint_id not in self.strategy_influence:
            return 0.0

        base_penalty = self.strategy_influence[constraint_id]["conflict_penalty"]

        # Scale by crowding (more crowded = more conflict pain)
        crowding = strategy_state.get("crowding_score", 0)
        penalty = base_penalty * (1 + crowding * 0.5)

        return min(0.20, penalty)

    def compute_meta_cognition_gate(
        self,
        bias_signals: Dict[str, float]
    ) -> float:
        """
        Compute meta-cognition gate [0, 1].

        Lower values reduce all likelihoods (system is uncertain about itself).
        """
        overconf = bias_signals.get("overconfidence_flag", 0)
        confirm = bias_signals.get("confirmation_bias_risk", 0)
        hindsight = bias_signals.get("hindsight_trap_flag", 0)

        # Gate reduces with each meta-bias
        gate = 1.0

        if overconf > self.meta_thresholds["overconfidence_gate"]:
            gate *= (1.0 - (overconf - 0.7) * 0.5)  # Up to 15% reduction

        if confirm > self.meta_thresholds["confirmation_bias_gate"]:
            gate *= (1.0 - (confirm - 0.6) * 0.4)  # Up to 16% reduction

        if hindsight > self.meta_thresholds["hindsight_trap_gate"]:
            gate *= (1.0 - (hindsight - 0.5) * 0.3)  # Up to 15% reduction

        return max(0.5, gate)  # Never reduce more than 50%

    def compute_enhanced_beliefs(
        self,
        signals: Dict[str, Any],
        session_phase: int,
        dvs: float,
        eqs: float,
        bias_signals: Optional[Dict[str, float]] = None,
        strategy_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, EnhancedConstraintLikelihood]:
        """
        Compute beliefs with full bias and strategy integration.

        This is the main entry point that incorporates all 300 pieces.
        """
        bias_signals = bias_signals or {}
        strategy_state = strategy_state or {}

        # Compute meta-cognition gate (applies to all constraints)
        meta_gate = self.compute_meta_cognition_gate(bias_signals)

        beliefs: Dict[str, EnhancedConstraintLikelihood] = {}

        for constraint_id in self.extended_matrix.keys():
            # 1. Compute extended evidence (includes bias signals)
            evidence = self.compute_extended_evidence(
                constraint_id, signals, bias_signals
            )

            # 2. Transform to raw likelihood
            likelihood_raw = self.compute_likelihood(constraint_id, evidence)

            # 3. Check applicability (time/DVS/EQS gates)
            applicability = self.check_applicability(
                constraint_id, session_phase, dvs, eqs
            )

            # 4. Compute bias adjustment
            bias_adj = self.compute_bias_adjustment(constraint_id, bias_signals)

            # 5. Compute strategy adjustment
            strategy_adj = self.compute_strategy_adjustment(
                constraint_id, strategy_state
            )

            # 6. Compute conflict penalty
            conflict_pen = self.compute_conflict_penalty(
                constraint_id, strategy_state
            )

            # 7. Apply adjustments
            adjusted_likelihood = likelihood_raw + bias_adj + strategy_adj - conflict_pen

            # 8. Apply decay
            decayed_likelihood = self.apply_decay(constraint_id, adjusted_likelihood)

            # 9. Apply meta-cognition gate
            gated_likelihood = decayed_likelihood * meta_gate

            # 10. Apply applicability
            final_likelihood = gated_likelihood * applicability

            # 11. Update stability
            self.update_stability(constraint_id, decayed_likelihood)

            # 12. Store result
            beliefs[constraint_id] = EnhancedConstraintLikelihood(
                constraint_id=constraint_id,
                evidence=evidence,
                likelihood=decayed_likelihood,
                applicability=applicability,
                effective_likelihood=final_likelihood,
                stability=self.stability_ewma.get(constraint_id, 0.0),
                decay_lambda=self.decay_lambdas.get(constraint_id, 0.95),
                # Enhanced fields
                bias_adjustment=bias_adj,
                strategy_adjustment=strategy_adj,
                conflict_penalty=conflict_pen,
                meta_cognition_gate=meta_gate,
                raw_likelihood=likelihood_raw,
                final_likelihood=final_likelihood,
            )

        return beliefs

    def get_top_constraints_enhanced(
        self,
        beliefs: Dict[str, EnhancedConstraintLikelihood],
        min_final_likelihood: float = 0.55,
        max_conflict_penalty: float = 0.15
    ) -> List[str]:
        """
        Get top constraints with enhanced filtering.

        Filters by final likelihood and conflict penalty.
        """
        viable = [
            (cid, belief)
            for cid, belief in beliefs.items()
            if (belief.final_likelihood >= min_final_likelihood and
                belief.conflict_penalty <= max_conflict_penalty)
        ]

        # Sort by final likelihood
        viable.sort(key=lambda x: x[1].final_likelihood, reverse=True)

        return [cid for cid, _ in viable]


# Factory function for easy instantiation
def create_enhanced_belief_engine() -> BeliefEngineV3:
    """Create enhanced belief engine with all 300 biases/strategies integrated."""
    return BeliefEngineV3()
