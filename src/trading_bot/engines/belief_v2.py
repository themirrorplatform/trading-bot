"""
Belief Engine V2 - Enhanced Constraint Likelihood System
Implements full constraint-signal matrix with sigmoid likelihood calculations.

Per specification:
- Constraint-signal matrix with explicit weights
- Likelihood: L_i = sigmoid(a_i * evidence + b_i)
- Per-constraint decay lambdas (F1=0.96, F3=0.98, F4=0.95, F5=0.94, F6=0.97)
- Applicability gating by time/DVS/EQS
- Stability tracking via EWMA

Expression Templates (Constraints):
- F1 (K1): VWAP Mean Reversion
- F3 (K2): Failed Break Fade
- F4 (K3): Sweep Reversal
- F5 (K4): Momentum Continuation
- F6: Noise Filter (always applicable)
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import json
import math
from decimal import Decimal


@dataclass
class ConstraintLikelihood:
    """Likelihood computation result for a constraint"""
    constraint_id: str
    evidence: float  # Weighted signal evidence
    likelihood: float  # Sigmoid transformed [0, 1]
    applicability: float  # Gate [0, 1] based on time/DVS/EQS
    effective_likelihood: float  # likelihood * applicability
    stability: float  # EWMA of |Δlikelihood|
    decay_lambda: float  # Decay rate used


class BeliefEngineV2:
    """
    Enhanced belief engine with constraint-signal matrix and likelihood calculations.

    Implements:
    - Explicit constraint-signal weight matrix
    - Sigmoid likelihood transformation: L = 1 / (1 + exp(-(a*evidence + b)))
    - Per-constraint decay lambdas for temporal smoothing
    - Applicability gating (time-of-day, DVS, EQS)
    - Stability tracking via EWMA
    - Optional learned parameters from Evolution Engine
    """

    def __init__(self, learned_params_path: Optional[str] = None):
        # Constraint-Signal Matrix
        # Format: {constraint_id: {signal_name: weight}}
        self.constraint_signal_matrix = self._build_constraint_signal_matrix()
        
        # Sigmoid parameters per constraint
        # Format: {constraint_id: {"a": slope, "b": bias}}
        self.sigmoid_params = {
            "F1": {"a": 1.8, "b": 0.4},   # VWAP MR: slight positive bias
            "F3": {"a": 2.5, "b": -0.5},  # Failed break: bias toward entry
            "F4": {"a": 3.0, "b": 0.0},   # Sweep reversal: sharp decision
            "F5": {"a": 2.0, "b": 0.5},   # Momentum: bias toward trend
            "F6": {"a": 1.5, "b": 0.0},   # Noise filter: gentle slope
        }
        
        # Decay lambdas per constraint (higher = slower adaptation)
        self.decay_lambdas = {
            "F1": 0.96,  # VWAP MR: slow decay (stable pattern)
            "F3": 0.98,  # Failed break: very slow (structural)
            "F4": 0.95,  # Sweep reversal: faster (transient)
            "F5": 0.94,  # Momentum: fastest (trend changes)
            "F6": 0.97,  # Noise filter: stable
        }
        
        # Applicability rules per constraint
        # Format: {constraint_id: {gate_type: threshold}}
        self.applicability_rules = {
            "F1": {"phases": [1, 2, 4, 5], "min_dvs": 0.80, "min_eqs": 0.75},
            "F3": {"phases": [1, 2], "min_dvs": 0.85, "min_eqs": 0.80},  # Stricter
            "F4": {"phases": [1, 2, 4], "min_dvs": 0.85, "min_eqs": 0.80},
            "F5": {"phases": [1, 2, 4], "min_dvs": 0.80, "min_eqs": 0.75},
            "F6": {"phases": [0, 1, 2, 3, 4, 5, 6], "min_dvs": 0.60, "min_eqs": 0.60},  # Always applicable
        }
        
        # Prior beliefs (for decay)
        self.prior_beliefs: Dict[str, float] = {}
        
        # Stability tracking (EWMA of |Δlikelihood|)
        self.stability_ewma: Dict[str, float] = {}
        self.stability_alpha = 0.2  # EWMA smoothing factor

        # Load learned parameters if available
        self._load_learned_params(learned_params_path)

    def _load_learned_params(self, params_path: Optional[str]) -> None:
        """
        Load learned parameters from Evolution Engine.

        Updates:
        - constraint_signal_matrix weights
        - decay_lambdas

        Args:
            params_path: Path to learned_params.json
        """
        if params_path is None:
            params_path = "data/learned_params.json"

        path = Path(params_path)
        if not path.exists():
            return

        try:
            with open(path, "r") as f:
                params = json.load(f)

            # Apply learned signal weights
            learned_weights = params.get("signal_weights", {})
            for constraint_id, signals in learned_weights.items():
                if constraint_id in self.constraint_signal_matrix:
                    for signal_name, weight in signals.items():
                        if signal_name in self.constraint_signal_matrix[constraint_id]:
                            self.constraint_signal_matrix[constraint_id][signal_name] = weight

            # Apply learned decay rates
            learned_decay = params.get("decay_rates", {})
            for constraint_id, rate in learned_decay.items():
                if constraint_id in self.decay_lambdas:
                    self.decay_lambdas[constraint_id] = rate

            version = params.get("version", 0)
            if version > 0:
                import logging
                logging.getLogger(__name__).info(
                    f"Loaded learned parameters v{version} from {params_path}"
                )

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Could not load learned params: {e}")

    def _build_constraint_signal_matrix(self) -> Dict[str, Dict[str, float]]:
        """
        Build explicit constraint-signal weight matrix.
        
        Each constraint has specific signals it cares about with explicit weights.
        Weights sum to 1.0 within each constraint for interpretability.
        """
        return {
            # F1 (K1): VWAP Mean Reversion
            # Cares about: VWAP distance, range compression, low volume, session phase
            "F1": {
                "vwap_z": 0.40,  # Primary: distance from VWAP
                "range_compression": 0.20,  # Tight range = potential reversion
                "vol_z": -0.15,  # Low volume = cleaner signal (negative weight)
                "close_location_value": 0.15,  # Position in bar
                "friction_regime_index": 0.10,  # Cost viability
            },
            
            # F3 (K2): Failed Break Fade
            # Cares about: breakout failure, rejection wick, volume, session
            "F3": {
                "breakout_distance_n": 0.30,  # Attempted breakout
                "rejection_wick_n": 0.30,  # Strong rejection
                "vol_z": 0.20,  # Volume on failure
                "hhll_trend_strength": -0.10,  # Weak trend (negative)
                "opening_range_break": 0.10,  # OR context
            },
            
            # F4 (K3): Sweep Reversal
            # Cares about: sweep pattern, volume climax, microstructure
            "F4": {
                "rejection_wick_n": 0.35,  # Sweep rejection
                "climax_bar_flag": 0.25,  # Volume spike
                "micro_trend_5": -0.15,  # Counter-trend (negative)
                "close_location_value": 0.15,  # Reversal close
                "distance_from_poc_proxy": 0.10,  # Away from value
            },
            
            # F5 (K4): Momentum Continuation
            # Cares about: trend strength, volume expansion, body impulse
            "F5": {
                "hhll_trend_strength": 0.30,  # Strong trend
                "micro_trend_5": 0.25,  # Aligned momentum
                "real_body_impulse_n": 0.20,  # Impulsive move
                "range_expansion_on_volume": 0.15,  # Healthy expansion
                "participation_expansion_index": 0.10,  # Growing participation
            },
            
            # F6: Noise Filter (always running)
            # Cares about: data quality, friction, session context
            "F6": {
                "dvs": 0.40,  # Data quality
                "friction_regime_index": 0.30,  # Cost regime
                "lunch_void_gate": 0.15,  # Avoid lunch
                "spread_proxy_tickiness": 0.10,  # Execution quality
                "slippage_risk_proxy": 0.05,  # Cost predictability
            },
        }
    
    def compute_evidence(self, constraint_id: str, signals: Dict[str, Any]) -> float:
        """
        Compute weighted evidence for a constraint from signals.
        
        Evidence = Σ(weight_i * signal_i) / Σ(|weight_i|)
        
        Args:
            constraint_id: Constraint to compute evidence for
            signals: Dictionary of signal values
        
        Returns:
            Normalized evidence in roughly [-1, 1] range (depends on signal ranges)
        """
        if constraint_id not in self.constraint_signal_matrix:
            return 0.0
        
        weights = self.constraint_signal_matrix[constraint_id]
        evidence = 0.0
        total_abs_weight = 0.0
        
        for signal_name, weight in weights.items():
            signal_value = signals.get(signal_name)
            
            # Handle None values
            if signal_value is None:
                continue
            
            # Convert to float
            try:
                if isinstance(signal_value, (Decimal, int)):
                    signal_value = float(signal_value)
                else:
                    signal_value = float(signal_value)
            except (TypeError, ValueError):
                continue
            
            evidence += weight * signal_value
            total_abs_weight += abs(weight)
        
        # Normalize by total absolute weight
        if total_abs_weight > 0:
            evidence /= total_abs_weight
        
        return evidence
    
    def compute_likelihood(self, constraint_id: str, evidence: float) -> float:
        """
        Transform evidence to likelihood via sigmoid.
        
        L_i = 1 / (1 + exp(-(a_i * evidence + b_i)))
        
        Args:
            constraint_id: Constraint ID
            evidence: Weighted signal evidence
        
        Returns:
            Likelihood in [0, 1]
        """
        if constraint_id not in self.sigmoid_params:
            # Default sigmoid
            return 1.0 / (1.0 + math.exp(-evidence))
        
        params = self.sigmoid_params[constraint_id]
        a = params["a"]
        b = params["b"]
        
        # Sigmoid with custom slope and bias
        logit = a * evidence + b
        
        # Prevent overflow
        if logit > 20:
            return 1.0
        elif logit < -20:
            return 0.0
        
        return 1.0 / (1.0 + math.exp(-logit))
    
    def check_applicability(
        self, 
        constraint_id: str, 
        session_phase: int, 
        dvs: float, 
        eqs: float
    ) -> float:
        """
        Check if constraint is applicable given current context.
        
        Applicability is a soft gate [0, 1]:
        - 1.0 = fully applicable
        - 0.0 = not applicable
        - (0, 1) = partial applicability (gradual degradation)
        
        Args:
            constraint_id: Constraint to check
            session_phase: Current session phase (0-6)
            dvs: Data Validity Score
            eqs: Execution Quality Score
        
        Returns:
            Applicability score [0, 1]
        """
        if constraint_id not in self.applicability_rules:
            return 1.0  # Default: fully applicable
        
        rules = self.applicability_rules[constraint_id]
        
        # Phase gate (hard)
        allowed_phases = rules.get("phases", [])
        if session_phase not in allowed_phases:
            return 0.0
        
        # DVS gate (soft)
        min_dvs = rules.get("min_dvs", 0.0)
        if dvs < min_dvs:
            # Linear degradation below threshold
            dvs_gate = max(0.0, dvs / min_dvs)
        else:
            dvs_gate = 1.0
        
        # EQS gate (soft)
        min_eqs = rules.get("min_eqs", 0.0)
        if eqs < min_eqs:
            eqs_gate = max(0.0, eqs / min_eqs)
        else:
            eqs_gate = 1.0
        
        # Combine gates (multiplicative: all must pass)
        applicability = dvs_gate * eqs_gate
        
        return applicability
    
    def apply_decay(self, constraint_id: str, current_likelihood: float) -> float:
        """
        Apply temporal decay to blend current likelihood with prior.
        
        L_t = (1 - λ) * L_current + λ * L_prior
        
        Higher λ = slower adaptation (more memory)
        
        Args:
            constraint_id: Constraint ID
            current_likelihood: Current bar's likelihood
        
        Returns:
            Decayed likelihood
        """
        lambda_decay = self.decay_lambdas.get(constraint_id, 0.95)
        prior = self.prior_beliefs.get(constraint_id, 0.5)  # Neutral prior
        
        decayed = (1.0 - lambda_decay) * current_likelihood + lambda_decay * prior
        
        # Update prior for next iteration
        self.prior_beliefs[constraint_id] = decayed
        
        return decayed
    
    def update_stability(self, constraint_id: str, current_likelihood: float):
        """
        Update stability metric via EWMA of |Δlikelihood|.
        
        Stability_t = α * |L_t - L_{t-1}| + (1 - α) * Stability_{t-1}
        
        Lower stability = more volatile belief = less reliable
        
        Args:
            constraint_id: Constraint ID
            current_likelihood: Current likelihood value
        """
        prior = self.prior_beliefs.get(constraint_id, 0.5)
        delta = abs(current_likelihood - prior)
        
        prior_stability = self.stability_ewma.get(constraint_id, 0.0)
        new_stability = self.stability_alpha * delta + (1.0 - self.stability_alpha) * prior_stability
        
        self.stability_ewma[constraint_id] = new_stability
    
    def compute_beliefs(
        self, 
        signals: Dict[str, Any], 
        session_phase: int,
        dvs: float,
        eqs: float
    ) -> Dict[str, ConstraintLikelihood]:
        """
        Compute beliefs for all constraints.
        
        Pipeline:
        1. Compute evidence from signals (weighted combination)
        2. Transform evidence to likelihood (sigmoid)
        3. Check applicability (time/DVS/EQS gates)
        4. Apply temporal decay (blend with prior)
        5. Update stability (EWMA of change)
        
        Args:
            signals: Dictionary of signal values (output from SignalEngineV2)
            session_phase: Current session phase (0-6)
            dvs: Data Validity Score
            eqs: Execution Quality Score
        
        Returns:
            Dictionary of {constraint_id: ConstraintLikelihood}
        """
        beliefs: Dict[str, ConstraintLikelihood] = {}
        
        for constraint_id in self.constraint_signal_matrix.keys():
            # 1. Compute evidence
            evidence = self.compute_evidence(constraint_id, signals)
            
            # 2. Transform to likelihood
            likelihood_raw = self.compute_likelihood(constraint_id, evidence)
            
            # 3. Check applicability
            applicability = self.check_applicability(constraint_id, session_phase, dvs, eqs)
            
            # 4. Apply decay
            likelihood_decayed = self.apply_decay(constraint_id, likelihood_raw)
            
            # 5. Update stability
            self.update_stability(constraint_id, likelihood_decayed)
            
            # 6. Compute effective likelihood
            effective_likelihood = likelihood_decayed * applicability
            
            # 7. Store result
            beliefs[constraint_id] = ConstraintLikelihood(
                constraint_id=constraint_id,
                evidence=evidence,
                likelihood=likelihood_decayed,
                applicability=applicability,
                effective_likelihood=effective_likelihood,
                stability=self.stability_ewma.get(constraint_id, 0.0),
                decay_lambda=self.decay_lambdas.get(constraint_id, 0.95)
            )
        
        return beliefs
    
    def get_top_constraints(
        self, 
        beliefs: Dict[str, ConstraintLikelihood], 
        min_likelihood: float = 0.5,
        min_applicability: float = 0.5
    ) -> List[str]:
        """
        Get top constraints sorted by effective likelihood.
        
        Filters by minimum likelihood and applicability thresholds.
        
        Args:
            beliefs: Belief computation results
            min_likelihood: Minimum likelihood threshold
            min_applicability: Minimum applicability threshold
        
        Returns:
            List of constraint IDs sorted by effective_likelihood (descending)
        """
        # Filter by thresholds
        viable = [
            (cid, belief) 
            for cid, belief in beliefs.items()
            if belief.likelihood >= min_likelihood and belief.applicability >= min_applicability
        ]
        
        # Sort by effective likelihood
        viable.sort(key=lambda x: x[1].effective_likelihood, reverse=True)
        
        return [cid for cid, _ in viable]
    
    def reset_state(self):
        """Reset all temporal state (for session boundaries or testing)"""
        self.prior_beliefs = {}
        self.stability_ewma = {}


def compute_beliefs_legacy(
    signals_payload: Dict[str, Any], 
    prev_beliefs: Dict[str, Any], 
    cfg: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Legacy wrapper for backward compatibility with existing code.
    
    Converts old API to new BeliefEngineV2.
    """
    engine = BeliefEngineV2()
    
    # Extract context
    session_phase = signals_payload.get("session_phase", 0)
    dvs = signals_payload.get("dvs", 1.0)
    eqs = signals_payload.get("eqs", 1.0)
    
    # Compute beliefs
    beliefs = engine.compute_beliefs(signals_payload, session_phase, dvs, eqs)
    
    # Get top constraints
    top_constraints = engine.get_top_constraints(beliefs)
    
    # Convert to legacy format
    beliefs_dict = {cid: belief.effective_likelihood for cid, belief in beliefs.items()}
    stability_dict = {cid: belief.stability for cid, belief in beliefs.items()}
    
    return {
        "beliefs": beliefs_dict,
        "stability": stability_dict,
        "top_constraints": top_constraints,
        "metadata": {
            "session_phase": session_phase,
            "dvs": dvs,
            "eqs": eqs,
        }
    }
