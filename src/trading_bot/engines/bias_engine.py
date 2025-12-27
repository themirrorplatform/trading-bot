"""
Bias Engine - Detects and scores active market biases.

Outputs BiasState each cycle with active biases, regime classification, and conflicts.
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import asdict
import importlib

from trading_bot.core.bias_strategy_types import BiasSpec, BiasState, BiasCategory
from trading_bot.engines.detectors import get_detector


class BiasEngine:
    """Computes BiasState from bar + signals + context."""
    
    def __init__(self, registry_path: str = None):
        if registry_path is None:
            registry_path = Path(__file__).parent.parent / "contracts" / "bias_registry.yaml"
        
        self.registry_path = Path(registry_path)
        self.biases: Dict[str, BiasSpec] = {}
        self._load_registry()
    
    def _load_registry(self):
        """Load bias registry from YAML."""
        with open(self.registry_path, "r") as f:
            data = yaml.safe_load(f)
        
        for bias_data in data.get("biases", []):
            spec = BiasSpec(
                id=bias_data["id"],
                category=BiasCategory(bias_data["category"]),
                inputs=bias_data["inputs"],
                detectors=bias_data["detectors"],
                strength_fn=bias_data["strength_fn"],
                confidence_fn=bias_data["confidence_fn"],
                invalidation=bias_data["invalidation"],
                conflicts_with=bias_data.get("conflicts_with", []),
                supports=bias_data.get("supports", []),
                tags=bias_data.get("tags", []),
                capital_tier_min=bias_data.get("capital_tier_min", "S")
            )
            self.biases[spec.id] = spec
    
    def compute(self, bar: Dict[str, Any], signals: Dict[str, Any], context: Dict[str, Any]) -> BiasState:
        """Compute BiasState for current bar."""
        active_biases = []
        
        for bias_id, bias_spec in self.biases.items():
            # Run detectors
            detector_scores = {}
            for detector_id in bias_spec.detectors:
                detector = get_detector(detector_id)
                if detector:
                    score = detector.detect(bar, signals, context)
                    detector_scores[detector_id] = score
            
            # Compute strength and confidence
            strength = self._call_scoring_fn(bias_spec.strength_fn, detector_scores, signals, context)
            confidence = self._call_scoring_fn(bias_spec.confidence_fn, detector_scores, signals, context)
            
            # Activation threshold
            if strength > 0.3 and confidence > 0.5:
                active_biases.append({
                    "bias_id": bias_id,
                    "strength": strength,
                    "confidence": confidence,
                    "category": bias_spec.category.value,
                    "expires_at": None  # TODO: implement time decay
                })
        
        # Regime classification
        regime = self._classify_regime(active_biases, signals)
        
        # Detect conflicts
        conflicts = self._detect_conflicts(active_biases)
        
        return BiasState(
            active=active_biases,
            regime=regime,
            conflicts=conflicts
        )
    
    def _call_scoring_fn(self, fn_path: str, detector_scores: Dict[str, float], 
                        signals: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Dynamically call scoring function."""
        try:
            module_name, fn_name = fn_path.rsplit(".", 1)
            module = importlib.import_module(f"trading_bot.engines.{module_name}")
            fn = getattr(module, fn_name)
            return fn(detector_scores, signals, context)
        except Exception as e:
            # Fallback: average detector scores
            if detector_scores:
                return sum(detector_scores.values()) / len(detector_scores)
            return 0.0
    
    def _classify_regime(self, active_biases: List[Dict[str, Any]], signals: Dict[str, Any]) -> Dict[str, str]:
        """Classify market regime from active biases."""
        # Volatility regime
        vol_biases = [b for b in active_biases if b["category"] in ["VOLATILITY", "EXISTENTIAL"]]
        if any(b["bias_id"] in ["VOLATILITY_EXPANSION_BIAS", "LIQUIDITY_VACUUM_BIAS"] for b in vol_biases):
            vol_regime = "HIGH"
        elif any(b["bias_id"] in ["DEAD_MARKET_BIAS", "MARKET_SILENCE_BIAS"] for b in vol_biases):
            vol_regime = "LOW"
        else:
            vol_regime = "NORMAL"
        
        # Trend regime
        trend_biases = [b for b in active_biases if "TREND" in b["bias_id"]]
        range_biases = [b for b in active_biases if "RANGE" in b["bias_id"] or "REVERSION" in b["bias_id"]]
        
        if trend_biases and not range_biases:
            trend_regime = "TRENDING"
        elif range_biases and not trend_biases:
            trend_regime = "RANGING"
        else:
            trend_regime = "MIXED"
        
        # Liquidity regime
        liq_biases = [b for b in active_biases if b["category"] == "LIQUIDITY"]
        if any(b["bias_id"] == "LIQUIDITY_VACUUM_BIAS" for b in liq_biases):
            liq_regime = "THIN"
        elif len(liq_biases) > 2:
            liq_regime = "ACTIVE"
        else:
            liq_regime = "NORMAL"
        
        return {
            "vol_regime": vol_regime,
            "trend_regime": trend_regime,
            "liquidity_regime": liq_regime
        }
    
    def _detect_conflicts(self, active_biases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect conflicting biases."""
        conflicts = []
        active_ids = {b["bias_id"] for b in active_biases}
        
        for bias in active_biases:
            bias_spec = self.biases.get(bias["bias_id"])
            if not bias_spec:
                continue
            
            for conflict_id in bias_spec.conflicts_with:
                if conflict_id in active_ids:
                    # Calculate conflict severity
                    severity = min(bias["strength"], 
                                 next((b["strength"] for b in active_biases if b["bias_id"] == conflict_id), 0.0))
                    conflicts.append({
                        "a": bias["bias_id"],
                        "b": conflict_id,
                        "severity": severity
                    })
        
        return conflicts
