"""
Unified Orchestrator - The Complete Trading Engine

This is the main entry point that orchestrates all components:
1. SignalEngineV2 - Core 28 signals
2. BiasSignalEngine - 22 bias-derived signals (S29-S50)
3. BeliefEngineV3 - Enhanced beliefs with bias/strategy integration
4. StrategyDetector - Strategy recognition and conflict detection
5. ModifierRegistry - Context-based threshold adjustments
6. DecisionEngineV2 - Capital-tier gates and EUC scoring

The orchestrator implements the complete 300-bias/strategy framework
by routing signals through the appropriate engines and computing
the final trading decision.

Pipeline:
  BAR → Signals → BiasSignals → Strategies → Beliefs → Modifiers → Decision
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
from zoneinfo import ZoneInfo

from .signals_v2 import SignalEngineV2, SignalOutput
from .bias_signals import BiasSignalEngine, BiasSignalOutput
from .belief_v3 import BeliefEngineV3, EnhancedConstraintLikelihood
from .strategy_detector import StrategyDetector, StrategyState
from .modifier_registry import ModifierRegistry, ModifierResult
from .decision_v2 import DecisionEngineV2, DecisionResult, CapitalTier

ET = ZoneInfo("America/New_York")


@dataclass
class BarInput:
    """Input for a single bar"""
    timestamp: datetime
    open_price: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None


@dataclass
class PipelineState:
    """Complete state at each stage of the pipeline"""
    # Input
    bar: BarInput

    # Stage 1: Core Signals
    signals: Optional[SignalOutput] = None

    # Stage 2: Bias Signals
    bias_signals: Optional[BiasSignalOutput] = None

    # Stage 3: Strategy Detection
    strategy_state: Optional[StrategyState] = None

    # Stage 4: Beliefs
    beliefs: Optional[Dict[str, EnhancedConstraintLikelihood]] = None

    # Stage 5: Modifiers
    modifier_result: Optional[ModifierResult] = None
    effective_threshold: float = 0.0

    # Stage 6: Decision
    decision: Optional[DecisionResult] = None

    # Diagnostics
    pipeline_latency_ms: float = 0.0
    errors: List[str] = field(default_factory=list)


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator"""
    # Capital and risk
    equity: Decimal = Decimal("1000")
    max_daily_loss: Decimal = Decimal("30")
    current_daily_pnl: Decimal = Decimal("0")

    # Position state
    current_position: int = 0
    trades_today: int = 0

    # Quality scores (computed externally or defaulted)
    dvs: float = 1.0
    eqs: float = 1.0

    # Risk state
    kill_switch_active: bool = False
    consecutive_losses: int = 0

    # Base threshold
    base_threshold: float = 0.0

    # Recent trade outcomes (for meta-cognition)
    recent_trade_outcomes: List[float] = field(default_factory=list)

    # Session context
    session_open_price: Optional[Decimal] = None
    prev_close_price: Optional[Decimal] = None


class Orchestrator:
    """
    The unified trading engine orchestrating all components.

    This class is the single entry point for processing bars through
    the complete 300-bias/strategy framework.
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()

        # Initialize all engines
        self.signal_engine = SignalEngineV2()
        self.bias_engine = BiasSignalEngine()
        self.belief_engine = BeliefEngineV3()
        self.strategy_detector = StrategyDetector()
        self.modifier_registry = ModifierRegistry(self.config.base_threshold)
        self.decision_engine = DecisionEngineV2()

        # State tracking
        self._last_decision: Optional[DecisionResult] = None
        self._bar_count: int = 0

    def update_config(self, **kwargs):
        """Update orchestrator configuration"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    def process_bar(self, bar: BarInput) -> PipelineState:
        """
        Process a single bar through the complete pipeline.

        This is the main entry point for the trading system.
        Each bar flows through:
        1. Signal computation (28 core + 22 bias = 50 signals)
        2. Strategy detection and conflict analysis
        3. Belief computation with bias/strategy integration
        4. Threshold modification based on context
        5. Decision with capital-tier gates and EUC scoring

        Args:
            bar: Bar input with OHLCV and optional bid/ask

        Returns:
            PipelineState with complete state at each stage
        """
        import time
        start_time = time.perf_counter()

        state = PipelineState(bar=bar)

        try:
            # Stage 1: Compute core signals
            state.signals = self._compute_signals(bar)

            # Stage 2: Compute bias signals
            state.bias_signals = self._compute_bias_signals(bar, state.signals)

            # Stage 3: Detect strategies and conflicts
            state.strategy_state = self._detect_strategies(
                state.signals, state.bias_signals
            )

            # Stage 4: Compute beliefs
            state.beliefs = self._compute_beliefs(
                state.signals, state.bias_signals, state.strategy_state
            )

            # Stage 5: Apply modifiers
            state.effective_threshold, state.modifier_result = self._apply_modifiers(
                bar.timestamp, state.signals, state.bias_signals, state.strategy_state
            )

            # Stage 6: Make decision
            state.decision = self._make_decision(
                state.beliefs, state.signals, state.strategy_state,
                state.effective_threshold
            )

            self._last_decision = state.decision
            self._bar_count += 1

        except Exception as e:
            state.errors.append(f"Pipeline error: {str(e)}")

        state.pipeline_latency_ms = (time.perf_counter() - start_time) * 1000
        return state

    def _compute_signals(self, bar: BarInput) -> SignalOutput:
        """Stage 1: Compute core 28 signals"""
        return self.signal_engine.compute_signals(
            timestamp=bar.timestamp,
            open_price=bar.open_price,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            bid=bar.bid,
            ask=bar.ask,
            dvs=self.config.dvs,
            eqs=self.config.eqs
        )

    def _compute_bias_signals(
        self,
        bar: BarInput,
        signals: SignalOutput
    ) -> BiasSignalOutput:
        """Stage 2: Compute 22 bias-derived signals"""
        # Set session context
        if self.config.session_open_price:
            self.bias_engine.set_session_open(self.config.session_open_price)
        if self.config.prev_close_price:
            self.bias_engine.set_prev_close(self.config.prev_close_price)

        return self.bias_engine.compute_bias_signals(
            timestamp=bar.timestamp,
            close=bar.close,
            high=bar.high,
            low=bar.low,
            volume=bar.volume,
            atr_14=Decimal(str(signals.atr_14_n)) if signals.atr_14_n else None,
            vol_z=signals.vol_z,
            vwap=Decimal(str(signals.vwap_z)) if signals.vwap_z else None,
            session_phase=signals.session_phase,
            micro_trend_5=signals.micro_trend_5,
            climax_bar_flag=signals.climax_bar_flag,
            hhll_trend_strength=signals.hhll_trend_strength,
            range_compression=signals.range_compression,
            dvs=self.config.dvs,
            eqs=self.config.eqs,
            current_position=self.config.current_position,
            recent_trade_outcomes=self.config.recent_trade_outcomes
        )

    def _detect_strategies(
        self,
        signals: SignalOutput,
        bias_signals: BiasSignalOutput
    ) -> StrategyState:
        """Stage 3: Detect active strategies and conflicts"""
        # Convert signals to dict
        signals_dict = self._signals_to_dict(signals)
        bias_dict = self._bias_signals_to_dict(bias_signals)

        # Determine capital tier
        tier = self.decision_engine.determine_capital_tier(self.config.equity)

        return self.strategy_detector.compute_strategy_state(
            signals=signals_dict,
            bias_signals=bias_dict,
            capital_tier=tier.name
        )

    def _compute_beliefs(
        self,
        signals: SignalOutput,
        bias_signals: BiasSignalOutput,
        strategy_state: StrategyState
    ) -> Dict[str, EnhancedConstraintLikelihood]:
        """Stage 4: Compute enhanced beliefs"""
        signals_dict = self._signals_to_dict(signals)
        bias_dict = self._bias_signals_to_dict(bias_signals)
        strategy_dict = self.strategy_detector.get_strategy_state_dict(strategy_state)

        return self.belief_engine.compute_enhanced_beliefs(
            signals=signals_dict,
            session_phase=signals.session_phase,
            dvs=self.config.dvs,
            eqs=self.config.eqs,
            bias_signals=bias_dict,
            strategy_state=strategy_dict
        )

    def _apply_modifiers(
        self,
        timestamp: datetime,
        signals: SignalOutput,
        bias_signals: BiasSignalOutput,
        strategy_state: StrategyState
    ) -> Tuple[float, ModifierResult]:
        """Stage 5: Apply threshold modifiers"""
        signals_dict = self._signals_to_dict(signals)
        bias_dict = self._bias_signals_to_dict(bias_signals)
        strategy_dict = self.strategy_detector.get_strategy_state_dict(strategy_state)

        # Add DVS/EQS to signals dict
        signals_dict["dvs"] = self.config.dvs
        signals_dict["eqs"] = self.config.eqs

        return self.modifier_registry.get_effective_threshold(
            timestamp=timestamp,
            signals=signals_dict,
            bias_signals=bias_dict,
            strategy_state=strategy_dict,
            regime_state={}  # Could add regime detection here
        )

    def _make_decision(
        self,
        beliefs: Dict[str, EnhancedConstraintLikelihood],
        signals: SignalOutput,
        strategy_state: StrategyState,
        effective_threshold: float
    ) -> DecisionResult:
        """Stage 6: Make trading decision"""
        signals_dict = self._signals_to_dict(signals)

        # Add threshold adjustment from modifiers
        signals_dict["threshold_adjustment"] = effective_threshold

        # Build state dict for decision engine
        state = {
            "timestamp": signals.timestamp,
            "eqs": self.config.eqs,
            "dvs": self.config.dvs,
            "current_position": self.config.current_position,
            "trades_today": self.config.trades_today,
            "consecutive_losses": self.config.consecutive_losses,
            "daily_pnl": float(self.config.current_daily_pnl),
            "strategy_conflict": strategy_state.conflict_detected,
            "strategy_confluence": strategy_state.confluence_count,
        }

        # Build risk state
        risk_state = {
            "kill_switch_active": self.config.kill_switch_active,
            "daily_loss_usd": float(-self.config.current_daily_pnl) if self.config.current_daily_pnl < 0 else 0,
        }

        # Pass full belief objects to decision engine
        # The decision engine expects objects with effective_likelihood and stability attributes
        return self.decision_engine.decide(
            equity=self.config.equity,
            beliefs=beliefs,  # Pass full EnhancedConstraintLikelihood objects
            signals=signals_dict,
            state=state,
            risk_state=risk_state
        )

    def _signals_to_dict(self, signals: SignalOutput) -> Dict[str, Any]:
        """Convert SignalOutput to dictionary"""
        return {
            "vwap_z": signals.vwap_z,
            "vwap_slope": signals.vwap_slope,
            "atr_14_n": signals.atr_14_n,
            "range_compression": signals.range_compression,
            "hhll_trend_strength": signals.hhll_trend_strength,
            "breakout_distance_n": signals.breakout_distance_n,
            "rejection_wick_n": signals.rejection_wick_n,
            "close_location_value": signals.close_location_value,
            "gap_from_prev_close_n": signals.gap_from_prev_close_n,
            "distance_from_poc_proxy": signals.distance_from_poc_proxy,
            "micro_trend_5": signals.micro_trend_5,
            "real_body_impulse_n": signals.real_body_impulse_n,
            "vol_z": signals.vol_z,
            "vol_slope_20": signals.vol_slope_20,
            "effort_vs_result": signals.effort_vs_result,
            "range_expansion_on_volume": signals.range_expansion_on_volume,
            "climax_bar_flag": signals.climax_bar_flag,
            "quiet_bar_flag": signals.quiet_bar_flag,
            "consecutive_high_vol_bars": signals.consecutive_high_vol_bars,
            "participation_expansion_index": signals.participation_expansion_index,
            "session_phase": signals.session_phase,
            "opening_range_break": signals.opening_range_break,
            "lunch_void_gate": signals.lunch_void_gate,
            "close_magnet_index": signals.close_magnet_index,
            "spread_proxy_tickiness": signals.spread_proxy_tickiness,
            "slippage_risk_proxy": signals.slippage_risk_proxy,
            "friction_regime_index": signals.friction_regime_index,
            "dvs": signals.dvs,
        }

    def _bias_signals_to_dict(self, bias_signals: BiasSignalOutput) -> Dict[str, float]:
        """Convert BiasSignalOutput to dictionary"""
        return {
            "fomo_index": bias_signals.fomo_index,
            "panic_index": bias_signals.panic_index,
            "herding_score": bias_signals.herding_score,
            "greed_index": bias_signals.greed_index,
            "fear_index": bias_signals.fear_index,
            "euphoria_flag": bias_signals.euphoria_flag,
            "round_number_proximity": bias_signals.round_number_proximity,
            "gamma_exposure_proxy": bias_signals.gamma_exposure_proxy,
            "anchoring_level_distance": bias_signals.anchoring_level_distance,
            "recency_bias_score": bias_signals.recency_bias_score,
            "overnight_gap_bias": bias_signals.overnight_gap_bias,
            "opening_drive_exhaustion": bias_signals.opening_drive_exhaustion,
            "time_of_day_edge": bias_signals.time_of_day_edge,
            "day_of_week_edge": bias_signals.day_of_week_edge,
            "pre_event_compression": bias_signals.pre_event_compression,
            "post_event_expansion": bias_signals.post_event_expansion,
            "month_end_flow": bias_signals.month_end_flow,
            "quarter_end_flow": bias_signals.quarter_end_flow,
            "overconfidence_flag": bias_signals.overconfidence_flag,
            "confirmation_bias_risk": bias_signals.confirmation_bias_risk,
            "availability_bias_score": bias_signals.availability_bias_score,
            "hindsight_trap_flag": bias_signals.hindsight_trap_flag,
            "psychological_state_score": bias_signals.psychological_state_score,
            "structural_bias_score": bias_signals.structural_bias_score,
            "temporal_bias_score": bias_signals.temporal_bias_score,
            "meta_cognition_score": bias_signals.meta_cognition_score,
        }

    def reset_session(self):
        """Reset session state (call at session boundaries)"""
        self.signal_engine.reset_session_state()
        self.bias_engine.reset_session()
        self.belief_engine.reset_state()
        self._bar_count = 0

    def get_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostic information"""
        return {
            "bar_count": self._bar_count,
            "config": {
                "equity": float(self.config.equity),
                "capital_tier": self.decision_engine.determine_capital_tier(
                    self.config.equity
                ).name,
                "current_position": self.config.current_position,
                "trades_today": self.config.trades_today,
                "daily_pnl": float(self.config.current_daily_pnl),
                "dvs": self.config.dvs,
                "eqs": self.config.eqs,
            },
            "last_decision": {
                "action": self._last_decision.action if self._last_decision else None,
                "reason": str(self._last_decision.reason) if self._last_decision else None,
            } if self._last_decision else None,
        }


# Factory function
def create_orchestrator(
    equity: Decimal = Decimal("1000"),
    **kwargs
) -> Orchestrator:
    """Create orchestrator with given configuration"""
    config = OrchestratorConfig(equity=equity, **kwargs)
    return Orchestrator(config)


# Quick test function
def test_pipeline():
    """Quick test of the complete pipeline"""
    from datetime import datetime

    orchestrator = create_orchestrator(equity=Decimal("2000"))

    # Create test bar
    bar = BarInput(
        timestamp=datetime(2025, 1, 15, 10, 30, tzinfo=ET),
        open_price=Decimal("5600.00"),
        high=Decimal("5600.75"),
        low=Decimal("5599.75"),
        close=Decimal("5600.50"),
        volume=1200,
        bid=Decimal("5600.25"),
        ask=Decimal("5600.50")
    )

    # Process
    result = orchestrator.process_bar(bar)

    print(f"Pipeline latency: {result.pipeline_latency_ms:.2f}ms")
    print(f"Signals computed: {result.signals is not None}")
    print(f"Bias signals computed: {result.bias_signals is not None}")
    print(f"Strategies detected: {len(result.strategy_state.active_strategies) if result.strategy_state else 0}")
    print(f"Conflict detected: {result.strategy_state.conflict_detected if result.strategy_state else False}")
    print(f"Beliefs computed: {len(result.beliefs) if result.beliefs else 0}")
    print(f"Modifiers active: {len(result.modifier_result.active_modifiers) if result.modifier_result else 0}")
    print(f"Effective threshold: {result.effective_threshold:.3f}")
    print(f"Decision: {result.decision.action if result.decision else 'None'}")

    if result.errors:
        print(f"Errors: {result.errors}")

    return result


if __name__ == "__main__":
    test_pipeline()
