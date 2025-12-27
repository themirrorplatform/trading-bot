from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Literal
from enum import Enum


class BiasCategory(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    LIQUIDITY = "LIQUIDITY"
    TIME = "TIME"
    VOLATILITY = "VOLATILITY"
    PSYCHOLOGICAL = "PSYCHOLOGICAL"
    INSTITUTIONAL = "INSTITUTIONAL"
    INFORMATION = "INFORMATION"
    TECHNICAL = "TECHNICAL"
    META = "META"
    EXISTENTIAL = "EXISTENTIAL"


class StrategyClass(str, Enum):
    TREND = "TREND"
    MEAN_REVERSION = "MEAN_REVERSION"
    BREAKOUT = "BREAKOUT"
    RANGE = "RANGE"
    LIQUIDITY = "LIQUIDITY"
    ORDERFLOW = "ORDERFLOW"
    VOLATILITY = "VOLATILITY"
    TIME_BASED = "TIME_BASED"
    EVENT = "EVENT"
    PATTERN = "PATTERN"
    STATISTICAL = "STATISTICAL"
    SCALPING = "SCALPING"
    POSITION = "POSITION"
    OPTIONS = "OPTIONS"
    META = "META"


@dataclass
class BiasSpec:
    """Static registry definition of a market bias."""
    id: str
    category: BiasCategory
    inputs: List[str]  # Signal IDs
    detectors: List[str]  # Detector IDs
    strength_fn: str  # Python callable path
    confidence_fn: str
    invalidation: Dict[str, Any]  # conditions + time_decay
    conflicts_with: List[str] = field(default_factory=list)
    supports: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    capital_tier_min: str = "S"  # S, A, B


@dataclass
class StrategySpec:
    """Static registry definition of a trading strategy archetype."""
    id: str
    strategy_class: StrategyClass
    bias_dependencies: List[str]  # Bias IDs
    signature_detectors: List[str]
    success_metrics: List[str]
    failure_signatures: List[str] = field(default_factory=list)
    recommended_postures: List[Literal["ALIGN", "FADE", "STAND_DOWN"]] = field(default_factory=lambda: ["ALIGN"])
    risk_profile: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BiasState:
    """Runtime state of active biases."""
    active: List[Dict[str, Any]] = field(default_factory=list)  # {bias_id, strength, confidence, expires_at}
    regime: Dict[str, str] = field(default_factory=dict)  # {vol_regime, trend_regime, liquidity_regime}
    conflicts: List[Dict[str, Any]] = field(default_factory=list)  # {a, b, severity}


@dataclass
class StrategyState:
    """Runtime state of detected strategies."""
    active: List[Dict[str, Any]] = field(default_factory=list)  # {strategy_id, probability, posture}
    dominance: List[Dict[str, Any]] = field(default_factory=list)  # {strategy_id, dominance_score}
    traps: List[Dict[str, Any]] = field(default_factory=list)  # {strategy_id, trap_score}


@dataclass
class Permission:
    """Trade permission output from bias/strategy gates."""
    allow_trade: bool
    allowed_directions: List[Literal["LONG", "SHORT"]] = field(default_factory=list)
    allowed_playbooks: List[str] = field(default_factory=list)  # Strategy IDs
    max_risk_units: float = 1.0
    required_confirmation: List[str] = field(default_factory=list)  # Signal IDs
    stand_down_reason: str = ""
