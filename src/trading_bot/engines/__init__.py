"""
Trading Bot Engines - Complete 300 Bias/Strategy Framework

Core Engines:
- SignalEngineV2: 28 core signals
- BeliefEngineV2: Constraint-signal matrix with sigmoid likelihoods
- DecisionEngineV2: Capital tier gates + EUC scoring

Enhanced Engines (V3):
- BiasSignalEngine: 22 bias-derived signals (S29-S50)
- BeliefEngineV3: Enhanced beliefs with bias/strategy integration
- StrategyDetector: Strategy recognition + conflict detection
- ModifierRegistry: Context-based threshold adjustments
- AttributionEngineV3: Enhanced attribution with bias/strategy tracking
- Orchestrator: Unified pipeline tying everything together
"""

# Core V2 Engines
from .signals_v2 import SignalEngineV2, SignalOutput, SignalReliability
from .belief_v2 import BeliefEngineV2, ConstraintLikelihood
from .decision_v2 import (
    DecisionEngineV2,
    DecisionResult,
    CapitalTier,
    TierConstraints,
    EdgeUncertaintyCost,
)

# Enhanced V3 Engines
from .bias_signals import BiasSignalEngine, BiasSignalOutput
from .belief_v3 import BeliefEngineV3, EnhancedConstraintLikelihood
from .strategy_detector import (
    StrategyDetector,
    StrategySignature,
    StrategyCategory,
    StrategyState,
    ActiveStrategy,
    Direction,
)
from .modifier_registry import (
    ModifierRegistry,
    Modifier,
    ModifierCategory,
    ModifierResult,
    get_modified_threshold,
)
from .attribution_v3 import (
    AttributionEngineV3,
    AttributionCategory,
    AttributionResult,
    TradeSnapshot,
    TradeResult,
)
from .orchestrator import (
    Orchestrator,
    OrchestratorConfig,
    BarInput,
    PipelineState,
    create_orchestrator,
)

__all__ = [
    # Core V2
    "SignalEngineV2",
    "SignalOutput",
    "SignalReliability",
    "BeliefEngineV2",
    "ConstraintLikelihood",
    "DecisionEngineV2",
    "DecisionResult",
    "CapitalTier",
    "TierConstraints",
    "EdgeUncertaintyCost",
    # Enhanced V3 - Bias Signals
    "BiasSignalEngine",
    "BiasSignalOutput",
    # Enhanced V3 - Beliefs
    "BeliefEngineV3",
    "EnhancedConstraintLikelihood",
    # Enhanced V3 - Strategies
    "StrategyDetector",
    "StrategySignature",
    "StrategyCategory",
    "StrategyState",
    "ActiveStrategy",
    "Direction",
    # Enhanced V3 - Modifiers
    "ModifierRegistry",
    "Modifier",
    "ModifierCategory",
    "ModifierResult",
    "get_modified_threshold",
    # Enhanced V3 - Attribution
    "AttributionEngineV3",
    "AttributionCategory",
    "AttributionResult",
    "TradeSnapshot",
    "TradeResult",
    # Orchestrator
    "Orchestrator",
    "OrchestratorConfig",
    "BarInput",
    "PipelineState",
    "create_orchestrator",
]
