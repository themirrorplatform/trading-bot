"""
Strategy Recognizer - Detects active strategy archetypes in the market.

Outputs StrategyState with dominant, trapped, and active strategies.
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, Any, List

from trading_bot.core.bias_strategy_types import StrategySpec, StrategyState, StrategyClass, BiasState
from trading_bot.engines.detectors import get_detector


class StrategyRecognizer:
    """Detects which strategy archetypes are active/dominant/trapped."""
    
    def __init__(self, registry_path: str = None):
        if registry_path is None:
            registry_path = Path(__file__).parent.parent / "contracts" / "strategy_registry.yaml"
        
        self.registry_path = Path(registry_path)
        self.strategies: Dict[str, StrategySpec] = {}
        self._load_registry()
    
    def _load_registry(self):
        """Load strategy registry from YAML."""
        with open(self.registry_path, "r") as f:
            data = yaml.safe_load(f)
        
        for strat_data in data.get("strategies", []):
            spec = StrategySpec(
                id=strat_data["id"],
                strategy_class=StrategyClass(strat_data["strategy_class"]),
                bias_dependencies=strat_data["bias_dependencies"],
                signature_detectors=strat_data["signature_detectors"],
                success_metrics=strat_data["success_metrics"],
                failure_signatures=strat_data.get("failure_signatures", []),
                recommended_postures=strat_data.get("recommended_postures", ["ALIGN"]),
                risk_profile=strat_data.get("risk_profile", {})
            )
            self.strategies[spec.id] = spec
    
    def compute(self, bar: Dict[str, Any], signals: Dict[str, Any], 
                bias_state: BiasState, context: Dict[str, Any]) -> StrategyState:
        """Compute StrategyState for current bar."""
        active_strategies = []
        dominance_scores = []
        trap_scores = []
        
        # Get active bias IDs
        active_bias_ids = {b["bias_id"] for b in bias_state.active}
        
        for strategy_id, strategy_spec in self.strategies.items():
            # Check bias dependencies
            required_biases = set(strategy_spec.bias_dependencies)
            bias_support = len(required_biases & active_bias_ids) / len(required_biases) if required_biases else 0.0
            
            # Run signature detectors
            signature_scores = []
            for detector_id in strategy_spec.signature_detectors:
                detector = get_detector(detector_id)
                if detector:
                    score = detector.detect(bar, signals, context)
                    signature_scores.append(score)
            
            signature_strength = sum(signature_scores) / len(signature_scores) if signature_scores else 0.0
            
            # Run failure detectors
            failure_scores = []
            for detector_id in strategy_spec.failure_signatures:
                detector = get_detector(detector_id)
                if detector:
                    score = detector.detect(bar, signals, context)
                    failure_scores.append(score)
            
            failure_strength = sum(failure_scores) / len(failure_scores) if failure_scores else 0.0
            
            # Overall probability
            probability = (bias_support * 0.5) + (signature_strength * 0.5)
            
            # Determine posture
            posture = "STAND_DOWN"
            if probability > 0.4:
                if failure_strength > 0.6:
                    posture = "FADE"  # Strategy is trapped
                    trap_scores.append({
                        "strategy_id": strategy_id,
                        "trap_score": failure_strength
                    })
                elif "ALIGN" in strategy_spec.recommended_postures:
                    posture = "ALIGN"
                    dominance_scores.append({
                        "strategy_id": strategy_id,
                        "dominance_score": probability * (1.0 - failure_strength)
                    })
                elif "FADE" in strategy_spec.recommended_postures and failure_strength > 0.3:
                    posture = "FADE"
            
            if probability > 0.3:
                active_strategies.append({
                    "strategy_id": strategy_id,
                    "probability": probability,
                    "posture": posture,
                    "strategy_class": strategy_spec.strategy_class.value
                })
        
        # Sort by scores
        dominance_scores = sorted(dominance_scores, key=lambda x: x["dominance_score"], reverse=True)
        trap_scores = sorted(trap_scores, key=lambda x: x["trap_score"], reverse=True)
        
        return StrategyState(
            active=active_strategies,
            dominance=dominance_scores[:5],  # Top 5 dominant
            traps=trap_scores[:5]  # Top 5 traps
        )
