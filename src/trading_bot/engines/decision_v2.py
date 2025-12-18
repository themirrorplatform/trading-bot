"""
Decision Engine V2 - Capital Tier Gates with Edge-Uncertainty-Cost Scoring

Implements constitutional hierarchy:
Layer 0: KILL_SWITCH
Layer 1: CONSTITUTION  
Layer 2: QUALITY_GATES (DVS, EQS)
Layer 3: SESSION_GATES
Layer 4: REGIME_LOCKOUTS
Layer 5: CAPITAL_TIER_GATES ← New
Layer 6: BELIEF_STABILITY_GATES
Layer 7: FRICTION_GATE
Layer 8: TEMPLATE_EXECUTION

Capital Tiers:
- S: Survival ($0-$2.5k) → K1, K2 templates, 10 tick max stop, $12 max risk
- A: Advancement ($2.5k-$7.5k) → K1, K2, K3, 14 tick max stop, $15 max risk
- B: Breakout ($7.5k+) → K1, K2, K3, K4, 18 tick max stop, $15 max risk

Edge-Uncertainty-Cost Scoring:
- Edge = E_R * P_lb (expected return × lower bound probability)
- Uncertainty = f(DVS, EQS, belief_stability)
- Cost = friction / expected_move
- Score = Edge - Uncertainty - Cost
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, time
from enum import Enum
import math

from ..core.reason_codes import NoTradeReason


class CapitalTier(Enum):
    """Capital tier classification"""
    S = "Survival"      # $0-$2.5k
    A = "Advancement"   # $2.5k-$7.5k
    B = "Breakout"      # $7.5k+


@dataclass
class TierConstraints:
    """Constraints for a capital tier"""
    tier: CapitalTier
    min_capital: Decimal
    max_capital: Optional[Decimal]
    allowed_templates: List[str]
    max_stop_ticks: int
    max_risk_usd: Decimal


@dataclass
class EdgeUncertaintyCost:
    """EUC scoring components"""
    edge: float             # Expected edge (E_R * P_lb)
    uncertainty: float      # Uncertainty penalty
    cost: float            # Friction cost penalty
    total_score: float     # edge - uncertainty - cost
    components: Dict[str, float]  # Breakdown for diagnostics


@dataclass
class DecisionResult:
    """Decision output"""
    action: str  # "NO_TRADE" or "ORDER_INTENT"
    reason: Optional[NoTradeReason]
    order_intent: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
    timestamp: datetime


class DecisionEngineV2:
    """
    Enhanced decision engine with capital tier gates and EUC scoring.
    """
    
    def __init__(self, contracts_path: str = "src/trading_bot/contracts"):
        self.contracts_path = contracts_path
        
        # Define tier constraints per constitution
        self.tier_constraints = {
            CapitalTier.S: TierConstraints(
                tier=CapitalTier.S,
                min_capital=Decimal("0"),
                max_capital=Decimal("2500"),
                allowed_templates=["K1", "K2"],
                max_stop_ticks=10,
                max_risk_usd=Decimal("12.00")
            ),
            CapitalTier.A: TierConstraints(
                tier=CapitalTier.A,
                min_capital=Decimal("2500"),
                max_capital=Decimal("7500"),
                allowed_templates=["K1", "K2", "K3"],
                max_stop_ticks=14,
                max_risk_usd=Decimal("15.00")
            ),
            CapitalTier.B: TierConstraints(
                tier=CapitalTier.B,
                min_capital=Decimal("7500"),
                max_capital=None,  # Open-ended
                allowed_templates=["K1", "K2", "K3", "K4"],
                max_stop_ticks=18,
                max_risk_usd=Decimal("15.00")
            ),
        }
        
        # Template definitions
        # Format: {template_id: {constraint_id, expected_return_ticks, target_ticks, stop_ticks, ...}}
        self.templates = {
            "K1": {
                "name": "VWAP Mean Reversion",
                "constraint_id": "F1",
                "expected_return_ticks": 12,
                "target_ticks": 16,
                "stop_ticks": 8,
                "time_stop_minutes": 30,
                "min_belief": 0.65,
                "capital_tiers": ["S", "A", "B"],
            },
            "K2": {
                "name": "Failed Break Fade",
                "constraint_id": "F3",
                "expected_return_ticks": 10,
                "target_ticks": 12,
                "stop_ticks": 10,
                "time_stop_minutes": 45,
                "min_belief": 0.70,
                "capital_tiers": ["S", "A", "B"],
            },
            "K3": {
                "name": "Sweep Reversal",
                "constraint_id": "F4",
                "expected_return_ticks": 12,
                "target_ticks": 15,
                "stop_ticks": 10,
                "time_stop_minutes": 40,
                "min_belief": 0.75,
                "capital_tiers": ["A", "B"],  # Not available in tier S
            },
            "K4": {
                "name": "Momentum Continuation",
                "constraint_id": "F5",
                "expected_return_ticks": 15,
                "target_ticks": 20,
                "stop_ticks": 12,
                "time_stop_minutes": 60,
                "min_belief": 0.70,
                "capital_tiers": ["B"],  # Only in tier B
            },
        }
        
        # Constitutional limits (hard caps)
        self.constitutional_max_risk = Decimal("15.00")
        self.constitutional_max_stop_ticks = 12
        self.tick_value = Decimal("1.25")  # MES: 1 tick = $1.25
        
        # EUC scoring parameters
        self.euc_params = {
            "min_edge": 0.10,  # Minimum edge required
            "max_uncertainty": 0.40,  # Maximum uncertainty tolerated
            "max_cost": 0.30,  # Maximum friction cost
            "min_total_score": 0.0,  # Minimum total EUC score
        }
    
    def determine_capital_tier(self, equity: Decimal) -> CapitalTier:
        """
        Determine capital tier based on current equity.
        
        Args:
            equity: Current account equity
        
        Returns:
            CapitalTier enum
        """
        if equity < Decimal("2500"):
            return CapitalTier.S
        elif equity < Decimal("7500"):
            return CapitalTier.A
        else:
            return CapitalTier.B
    
    def filter_templates_by_tier(self, tier: CapitalTier) -> List[str]:
        """
        Get allowed templates for capital tier.
        
        Args:
            tier: Capital tier
        
        Returns:
            List of allowed template IDs
        """
        tier_name = tier.name
        allowed = [
            template_id 
            for template_id, template in self.templates.items()
            if tier_name in template["capital_tiers"]
        ]
        return allowed
    
    def compute_effective_stop(
        self, 
        template_stop_ticks: int, 
        tier: CapitalTier,
        equity: Decimal
    ) -> int:
        """
        Compute effective stop size enforcing constitutional limits.
        
        Hierarchy:
        1. Constitutional max (12 ticks)
        2. Tier max (varies by tier)
        3. Template stop (from template definition)
        4. Risk-derived stop (from max_risk / tick_value)
        
        Effective stop = min(all limits)
        
        Args:
            template_stop_ticks: Stop from template definition
            tier: Capital tier
            equity: Current equity (for risk calculation)
        
        Returns:
            Effective stop in ticks
        """
        tier_constraints = self.tier_constraints[tier]
        
        # Get all limits
        constitutional_limit = self.constitutional_max_stop_ticks
        tier_limit = tier_constraints.max_stop_ticks
        template_limit = template_stop_ticks
        
        # Risk-derived limit (max risk / tick value)
        max_risk = min(self.constitutional_max_risk, tier_constraints.max_risk_usd)
        risk_derived_limit = int(max_risk / self.tick_value)
        
        # Take minimum of all limits
        effective_stop = min(
            constitutional_limit,
            tier_limit,
            template_limit,
            risk_derived_limit
        )
        
        return effective_stop
    
    def compute_edge(
        self, 
        template: Dict[str, Any],
        belief_likelihood: float,
        win_rate_estimate: float = 0.50  # Conservative default
    ) -> float:
        """
        Compute edge component of EUC score.
        
        Edge = E_R * P_lb
        
        Where:
        - E_R = expected return (template target - template stop) * tick_value
        - P_lb = lower bound win probability (conservative)
        
        Args:
            template: Template definition
            belief_likelihood: Constraint likelihood [0, 1]
            win_rate_estimate: Historical win rate (default: 50%)
        
        Returns:
            Edge score
        """
        expected_return_ticks = template["expected_return_ticks"]
        target_ticks = template["target_ticks"]
        stop_ticks = template["stop_ticks"]
        
        # Expected return calculation
        # E_R = (target - stop) * tick_value * win_rate - stop * tick_value * (1 - win_rate)
        # Simplified: E_R = expected_return_ticks (already accounts for this)
        
        # Lower bound probability: use belief with haircut (outcome-neutral learning)
        p_lb = max(0.0, min(1.0, belief_likelihood)) * 0.8
        
        # Edge in tick units
        edge_ticks = expected_return_ticks * p_lb
        
        # Normalize to [0, 1] scale (assuming max edge of 10 ticks)
        edge_normalized = min(1.0, edge_ticks / 10.0)
        
        return edge_normalized
    
    def compute_uncertainty(
        self,
        dvs: float,
        eqs: float,
        belief_stability: float,
        belief_likelihood: float
    ) -> float:
        """
        Compute uncertainty component of EUC score.
        
        Uncertainty reflects information quality and belief confidence.
        
        Components:
        - DVS degradation: 1 - DVS
        - EQS degradation: 1 - EQS  
        - Belief instability: stability (higher = more unstable)
        - Belief weakness: 1 - likelihood (lower belief = higher uncertainty)
        
        Args:
            dvs: Data Validity Score [0, 1]
            eqs: Execution Quality Score [0, 1]
            belief_stability: Belief stability metric [0, 1]
            belief_likelihood: Constraint likelihood [0, 1]
        
        Returns:
            Uncertainty score [0, 1] (higher = more uncertain)
        """
        dvs_uncertainty = 1.0 - dvs
        eqs_uncertainty = 1.0 - eqs
        stability_uncertainty = belief_stability  # Higher stability = less stable
        belief_uncertainty = 1.0 - belief_likelihood
        
        # Weighted combination
        uncertainty = (
            0.30 * dvs_uncertainty +
            0.25 * eqs_uncertainty +
            0.25 * stability_uncertainty +
            0.20 * belief_uncertainty
        )
        
        return min(1.0, uncertainty)
    
    def compute_cost(
        self,
        friction_usd: Decimal,
        expected_move_ticks: int,
        atr_14: Decimal
    ) -> float:
        """
        Compute cost component of EUC score.
        
        Cost = friction / expected_move
        
        Where:
        - friction = pessimistic roundtrip cost ($9 base + slippage)
        - expected_move = template target in dollars
        
        Args:
            friction_usd: Total friction cost (base + slippage)
            expected_move_ticks: Expected move in ticks
            atr_14: ATR(14) for volatility adjustment
        
        Returns:
            Cost score [0, 1] (higher = more costly)
        """
        expected_move_usd = Decimal(expected_move_ticks) * self.tick_value
        
        if expected_move_usd == 0:
            return 1.0  # Infinite cost
        
        cost_ratio = float(friction_usd / expected_move_usd)

        # Use raw ratio (0..1+) clamped; separate gates enforce max tolerable
        return min(1.0, cost_ratio)
    
    def compute_euc_score(
        self,
        template: Dict[str, Any],
        belief_likelihood: float,
        belief_stability: float,
        dvs: float,
        eqs: float,
        friction_usd: Decimal,
        atr_14: Decimal
    ) -> EdgeUncertaintyCost:
        """
        Compute Edge-Uncertainty-Cost score.
        
        Score = Edge - Uncertainty - Cost
        
        Args:
            template: Template definition
            belief_likelihood: Constraint likelihood
            belief_stability: Belief stability metric
            dvs: Data Validity Score
            eqs: Execution Quality Score
            friction_usd: Total friction cost
            atr_14: ATR(14)
        
        Returns:
            EdgeUncertaintyCost with components
        """
        # Compute components
        edge = self.compute_edge(template, belief_likelihood)
        uncertainty = self.compute_uncertainty(dvs, eqs, belief_stability, belief_likelihood)
        cost = self.compute_cost(friction_usd, template["target_ticks"], atr_14)
        
        # Total score
        total_score = edge - uncertainty - cost
        
        return EdgeUncertaintyCost(
            edge=edge,
            uncertainty=uncertainty,
            cost=cost,
            total_score=total_score,
            components={
                "edge": edge,
                "uncertainty": uncertainty,
                "cost": cost,
                "dvs_component": 1.0 - dvs,
                "eqs_component": 1.0 - eqs,
                "stability_component": belief_stability,
                "belief_component": 1.0 - belief_likelihood,
            }
        )
    
    def decide(
        self,
        equity: Decimal,
        beliefs: Dict[str, Any],  # From BeliefEngineV2
        signals: Dict[str, Any],  # From SignalEngineV2
        state: Dict[str, Any],
        risk_state: Dict[str, Any]
    ) -> DecisionResult:
        """
        Main decision function with capital tier gates and EUC scoring.
        
        Decision hierarchy:
        1. Kill switch
        2. Constitution gates (DVS, EQS)
        3. Session gates
        4. Regime lockouts
        5. Capital tier gates ← NEW
        6. Belief stability gates
        7. Friction gate
        8. Template selection via EUC scoring ← ENHANCED
        
        Args:
            equity: Current account equity
            beliefs: Belief computation results (from BeliefEngineV2)
            signals: Signal values (from SignalEngineV2)
            state: Bot state
            risk_state: Risk engine state
        
        Returns:
            DecisionResult
        """
        timestamp = state.get("timestamp", datetime.now())
        
        # Layer 0: Kill switch
        if risk_state.get("kill_switch_active", False):
            return DecisionResult(
                action="NO_TRADE",
                reason=NoTradeReason.KILL_SWITCH_ACTIVE,
                order_intent=None,
                metadata={"kill_switch_reason": risk_state.get("kill_switch_reason")},
                timestamp=timestamp
            )
        
        # Layer 1: Constitution gates (DVS, EQS)
        dvs = signals.get("dvs", 0.0)
        eqs = state.get("eqs", 0.0)
        
        if dvs < 0.80:
            return DecisionResult(
                action="NO_TRADE",
                reason=NoTradeReason.DVS_TOO_LOW,
                order_intent=None,
                metadata={"dvs": dvs, "threshold": 0.80},
                timestamp=timestamp
            )
        
        if eqs < 0.75:
            return DecisionResult(
                action="NO_TRADE",
                reason=NoTradeReason.EQS_TOO_LOW,
                order_intent=None,
                metadata={"eqs": eqs, "threshold": 0.75},
                timestamp=timestamp
            )
        
        # Layer 3: Session gates
        session_phase = signals.get("session_phase", 0)
        lunch_gate = signals.get("lunch_void_gate", 1.0)
        
        if lunch_gate == 0.0:  # Hard gate for lunch
            return DecisionResult(
                action="NO_TRADE",
                reason=NoTradeReason.SESSION_WINDOW_BLOCK,
                order_intent=None,
                metadata={"session_phase": session_phase},
                timestamp=timestamp
            )
        
        if session_phase not in [1, 2, 4, 5]:  # Only trade during RTH
            return DecisionResult(
                action="NO_TRADE",
                reason=NoTradeReason.SESSION_NOT_TRADABLE,
                order_intent=None,
                metadata={"session_phase": session_phase},
                timestamp=timestamp
            )
        
        # Layer 4: Regime lockouts (TODO: implement vol shock, execution danger, news shock)
        # Placeholder for now
        
        # Layer 5: Capital tier gates ← NEW
        tier = self.determine_capital_tier(equity)
        tier_constraints = self.tier_constraints[tier]
        allowed_templates = self.filter_templates_by_tier(tier)
        
        if not allowed_templates:
            return DecisionResult(
                action="NO_TRADE",
                reason=NoTradeReason.TEMPLATE_NOT_ALLOWED_BY_TIER,
                order_intent=None,
                metadata={"tier": tier.name, "equity": float(equity)},
                timestamp=timestamp
            )
        
        # Layer 6: Belief stability gates
        # Filter templates by belief likelihood and stability
        viable_templates = []
        
        for template_id in allowed_templates:
            template = self.templates[template_id]
            constraint_id = template["constraint_id"]
            
            # Get belief for this constraint
            constraint_belief = beliefs.get(constraint_id)
            if constraint_belief is None:
                continue
            
            # Check minimum belief threshold
            if constraint_belief.effective_likelihood < template["min_belief"]:
                continue
            
            # Check stability (lower is better)
            if constraint_belief.stability > 0.30:  # Too unstable
                continue
            
            viable_templates.append((template_id, template, constraint_belief))
        
        if not viable_templates:
            return DecisionResult(
                action="NO_TRADE",
                reason=NoTradeReason.BELIEF_TOO_LOW,
                order_intent=None,
                metadata={
                    "tier": tier.name,
                    "allowed_templates": allowed_templates,
                    "beliefs": {cid: beliefs[cid].effective_likelihood for cid in beliefs if cid in ["F1", "F3", "F4", "F5"]}
                },
                timestamp=timestamp
            )
        
        # Layer 7: Friction gate + Layer 8: Template selection via EUC scoring
        
        # Get friction estimate
        friction_base = Decimal("9.00")  # Pessimistic base
        spread_proxy = signals.get("spread_proxy_tickiness", 1.0)
        slippage_proxy = signals.get("slippage_risk_proxy", 1.0)
        
        # Adjust friction based on current conditions
        if spread_proxy < 0.8 or slippage_proxy < 0.8:
            friction_additional = Decimal("3.00")
        else:
            friction_additional = Decimal("0.00")
        
        total_friction = friction_base + friction_additional
        
        # Get ATR for cost calculation
        atr_14 = signals.get("atr_14_n", 1.0)  # Normalized ATR
        if atr_14 is None:
            atr_14 = 1.0
        atr_14_absolute = Decimal(str(atr_14)) * Decimal("3.0")  # Rough conversion to absolute
        
        # Score all viable templates with EUC
        template_scores = []
        
        for template_id, template, constraint_belief in viable_templates:
            # Compute EUC score
            euc = self.compute_euc_score(
                template=template,
                belief_likelihood=constraint_belief.effective_likelihood,
                belief_stability=constraint_belief.stability,
                dvs=dvs,
                eqs=eqs,
                friction_usd=total_friction,
                atr_14=atr_14_absolute
            )
            
            # Check EUC thresholds
            if euc.edge < self.euc_params["min_edge"]:
                continue  # Insufficient edge
            
            if euc.uncertainty > self.euc_params["max_uncertainty"]:
                continue  # Too uncertain
            
            if euc.cost > self.euc_params["max_cost"]:
                continue  # Too costly
            
            if euc.total_score < self.euc_params["min_total_score"]:
                continue  # Negative total score
            
            template_scores.append((template_id, template, constraint_belief, euc))
        
        if not template_scores:
            return DecisionResult(
                action="NO_TRADE",
                reason=NoTradeReason.EDGE_SCORE_BELOW_THETA,
                order_intent=None,
                metadata={
                    "tier": tier.name,
                    "friction_usd": float(total_friction),
                    "viable_templates_pre_euc": [tid for tid, _, _ in viable_templates]
                },
                timestamp=timestamp
            )
        
        # Select best template by EUC score
        template_scores.sort(key=lambda x: x[3].total_score, reverse=True)
        best_template_id, best_template, best_belief, best_euc = template_scores[0]
        
        # Compute effective stop
        effective_stop_ticks = self.compute_effective_stop(
            template_stop_ticks=best_template["stop_ticks"],
            tier=tier,
            equity=equity
        )
        
        # Create order intent
        # Direction determined by constraint belief (simplified: use signal direction)
        # For K1 (VWAP MR): if price > VWAP, go SHORT; if price < VWAP, go LONG
        # For K2, K3, K4: need more sophisticated direction logic
        
        vwap_z = signals.get("vwap_z", 0.0)
        direction = "SHORT" if vwap_z > 0 else "LONG"  # Simplified
        
        order_intent = {
            "direction": direction,
            "contracts": 1,  # Always 1 contract in v1
            "entry_type": "LIMIT",  # No market orders per execution contract
            "stop_ticks": effective_stop_ticks,
            "target_ticks": best_template["target_ticks"],
            "stop_order_type": "STOP_LIMIT",
            "target_order_type": "LIMIT",
            "strategy_id": best_template_id,
            "timestamp": timestamp,
            "metadata": {
                "tier": tier.name,
                "constraint_id": best_template["constraint_id"],
                "belief_likelihood": best_belief.effective_likelihood,
                "euc_score": best_euc.total_score,
                "euc_components": best_euc.components,
            }
        }
        
        return DecisionResult(
            action="ORDER_INTENT",
            reason=None,
            order_intent=order_intent,
            metadata={
                "tier": tier.name,
                "template_id": best_template_id,
                "euc_score": best_euc.total_score,
                "all_scores": [
                    {
                        "template_id": tid,
                        "euc_score": euc.total_score,
                        "edge": euc.edge,
                        "uncertainty": euc.uncertainty,
                        "cost": euc.cost
                    }
                    for tid, _, _, euc in template_scores
                ]
            },
            timestamp=timestamp
        )
