"""
Evolution Engine - Bounded learning from trading outcomes.

Implements weekly parameter updates based on attributed trades:
- Signal weights adjustment
- Belief threshold tuning
- Decay rate adaptation
- Template parameter refinement

All updates are bounded by constitutional constraints.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from zoneinfo import ZoneInfo

from trading_bot.log.event_store import EventStore
from trading_bot.engines.attribution_v2 import score_post_trade, PostTradeScores
from trading_bot.core.config import load_yaml_contract
from trading_bot.core.types import Event, stable_json, sha256_hex

logger = logging.getLogger(__name__)
ET = ZoneInfo("America/New_York")


@dataclass
class InTradeParamsState:
    """Learnable in-trade management parameters."""
    # Protection parameters
    k_protect: float = 1.0           # Protect after +1R
    k_lock: float = 0.25             # Lock +0.25R when protecting
    min_bars_before_protect: int = 3
    theta_protect: float = 0.20      # Min evidence for protection

    # Scaling parameters (R multiples)
    k_T1: float = 1.0                # First target
    k_T2: float = 2.0                # Second target
    k_scale1_lock: float = 0.5       # Lock after T1
    k_scale2_lock: float = 1.0       # Lock after T2

    # Runner parameters
    k_trail: float = 0.75            # Trail buffer in ATR
    theta_runner_entry: float = 0.40 # Min evidence for runner

    # Kill switch
    theta_kill: float = 0.70         # Emergency exit threshold

    # Evidence weights (must sum to 1)
    w_structure: float = 0.30
    w_pullback: float = 0.25
    w_momentum: float = 0.25
    w_signal: float = 0.20


@dataclass
class ParameterState:
    """Current learnable parameters with bounds."""
    # Signal weights for belief computation (constraint -> signal -> weight)
    signal_weights: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Belief thresholds for entry (constraint -> threshold)
    belief_thresholds: Dict[str, float] = field(default_factory=dict)

    # Decay lambdas for temporal smoothing
    decay_rates: Dict[str, float] = field(default_factory=dict)

    # Template-specific adjustments
    template_stop_buffers: Dict[str, int] = field(default_factory=dict)
    template_time_stops: Dict[str, int] = field(default_factory=dict)

    # In-trade management parameters
    in_trade: InTradeParamsState = field(default_factory=InTradeParamsState)

    # Metadata
    version: int = 1
    last_updated: Optional[str] = None
    update_reason: Optional[str] = None


@dataclass
class EvolutionResult:
    """Result of an evolution cycle."""
    success: bool
    trades_analyzed: int
    parameters_updated: int
    changes: Dict[str, Any]
    reason: str
    timestamp: str


class EvolutionEngine:
    """
    Bounded learning engine that updates parameters based on trade outcomes.

    Supports two modes:
    1. Real-time learning: Updates after each trade with smaller increments
    2. Batch learning: Weekly updates with larger allowed changes

    Constitutional constraints:
    - Parameter bounds: Cannot exceed min/max
    - Max change: Limited per update (scaled for mode)

    NEVER RIGHT CONSTITUTION:
    - Symmetric learning: unlearn from losses as fast as learn from wins
    - Belief confidence cap: 0.75 maximum (never believe we're fully right)
    - Decay toward neutral: parameters drift to defaults without confirmation
    - No success acceleration: win streaks don't compound learning rate
    """

    # Never Right constants
    MAX_BELIEF_CONFIDENCE = 0.75
    NEUTRAL_DECAY_PER_TRADE = 0.01  # Decay toward neutral each trade

    # Default bounds from constitution (weekly batch mode)
    BOUNDS = {
        "signal_weights": {"min": 0.0, "max": 1.5, "max_change": 0.05},
        "belief_thresholds": {"min": 0.50, "max": 0.95, "max_change": 0.01},
        "decay_rates": {"min": 0.90, "max": 0.995, "max_change": 0.005},
        "template_stop_buffers": {"min": -2, "max": 2, "max_change": 1},
        "template_time_stops": {"min": 10, "max": 60, "max_change": 2},
    }

    # In-trade parameter bounds
    IN_TRADE_BOUNDS = {
        "k_protect": {"min": 0.5, "max": 2.0, "max_change": 0.10},
        "k_lock": {"min": 0.0, "max": 0.5, "max_change": 0.05},
        "theta_protect": {"min": 0.0, "max": 0.5, "max_change": 0.02},
        "k_T1": {"min": 0.5, "max": 2.0, "max_change": 0.10},
        "k_T2": {"min": 1.0, "max": 4.0, "max_change": 0.15},
        "k_scale1_lock": {"min": 0.25, "max": 1.0, "max_change": 0.05},
        "k_scale2_lock": {"min": 0.5, "max": 1.5, "max_change": 0.05},
        "k_trail": {"min": 0.25, "max": 1.5, "max_change": 0.05},
        "theta_runner_entry": {"min": 0.2, "max": 0.6, "max_change": 0.02},
        "theta_kill": {"min": 0.5, "max": 0.9, "max_change": 0.02},
        "w_structure": {"min": 0.1, "max": 0.5, "max_change": 0.02},
        "w_pullback": {"min": 0.1, "max": 0.5, "max_change": 0.02},
        "w_momentum": {"min": 0.1, "max": 0.5, "max_change": 0.02},
        "w_signal": {"min": 0.05, "max": 0.4, "max_change": 0.02},
    }

    # Real-time learning uses smaller increments (1/20th of weekly for ~20 trades/week)
    REALTIME_SCALE = 0.05

    MIN_TRADES_FOR_UPDATE = 10

    # Meta-learner integration (optional)
    meta_learner = None

    def __init__(
        self,
        event_store: EventStore,
        contracts_path: str = "src/trading_bot/contracts",
        params_path: str = "data/learned_params.json",
    ):
        """
        Initialize evolution engine.

        Args:
            event_store: EventStore for querying trades
            contracts_path: Path to contract YAML files
            params_path: Path to persist learned parameters
        """
        self.event_store = event_store
        self.contracts_path = contracts_path
        self.params_path = Path(params_path)

        # Load constitution for bounds
        try:
            constitution = load_yaml_contract(contracts_path, "constitution.yaml")
            evolution = constitution.get("evolution_constraints", {})
            bounds = evolution.get("parameter_bounds", {})

            # Override defaults with constitution values
            for param_type, cfg in bounds.items():
                if param_type in self.BOUNDS:
                    self.BOUNDS[param_type]["min"] = cfg.get("min", self.BOUNDS[param_type]["min"])
                    self.BOUNDS[param_type]["max"] = cfg.get("max", self.BOUNDS[param_type]["max"])
                    self.BOUNDS[param_type]["max_change"] = cfg.get(
                        "max_change_per_week", self.BOUNDS[param_type]["max_change"]
                    )

            self.MIN_TRADES_FOR_UPDATE = evolution.get("min_trades_for_update", 10)

        except Exception as e:
            logger.warning(f"Could not load constitution bounds: {e}")

        # Load current parameters
        self.params = self._load_params()

        # Initialize defaults if empty
        if not self.params.signal_weights:
            self._init_default_params()

    def _load_params(self) -> ParameterState:
        """Load persisted parameters."""
        if self.params_path.exists():
            try:
                with open(self.params_path, "r") as f:
                    data = json.load(f)
                return ParameterState(**data)
            except Exception as e:
                logger.warning(f"Could not load params: {e}")

        return ParameterState()

    def _save_params(self) -> None:
        """Persist current parameters."""
        self.params_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.params_path, "w") as f:
            json.dump(asdict(self.params), f, indent=2)

    def _init_default_params(self) -> None:
        """Initialize with default parameter values."""
        # Default signal weights per constraint
        self.params.signal_weights = {
            "F1": {"vwap_z": 0.4, "vwap_slope": 0.2, "atr_14_n": 0.2, "vol_z": 0.2},
            "F3": {"breakout_distance_n": 0.5, "vol_z": 0.3, "hhll_trend_strength": 0.2},
            "F4": {"micro_trend_5": 0.4, "real_body_impulse_n": 0.3, "vol_slope_20": 0.3},
            "F5": {"vol_z": 0.4, "effort_vs_result": 0.3, "participation_expansion_index": 0.3},
            "F6": {"spread_proxy_tickiness": 0.4, "slippage_risk_proxy": 0.3, "friction_regime_index": 0.3},
        }

        # Default belief thresholds
        self.params.belief_thresholds = {
            "F1": 0.65,
            "F3": 0.60,
            "F4": 0.55,
            "F5": 0.50,
            "F6": 0.50,
        }

        # Default decay rates
        self.params.decay_rates = {
            "F1": 0.96,
            "F3": 0.98,
            "F4": 0.95,
            "F5": 0.94,
            "F6": 0.97,
        }

        # Default template adjustments (0 = no adjustment)
        self.params.template_stop_buffers = {"K1": 0, "K2": 0, "K3": 0, "K4": 0}
        self.params.template_time_stops = {"K1": 30, "K2": 25, "K3": 20, "K4": 15}

        self.params.last_updated = datetime.now(ET).isoformat()
        self.params.update_reason = "INITIALIZED_DEFAULTS"
        self._save_params()

    def get_attributed_trades(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query trades with attribution data.

        Args:
            since: Start of period (default: 7 days ago)
            until: End of period (default: now)

        Returns:
            List of attributed trade records
        """
        if since is None:
            since = datetime.now(ET) - timedelta(days=7)
        if until is None:
            until = datetime.now(ET)

        # Query FILL_EVENT and ATTRIBUTION events
        fills = self.event_store.query(
            event_type="FILL_EVENT",
            start_time=since.isoformat(),
            end_time=until.isoformat(),
            limit=500,
        )

        attributions = self.event_store.query(
            event_type="ATTRIBUTION",
            start_time=since.isoformat(),
            end_time=until.isoformat(),
            limit=500,
        )

        # Build attribution lookup by timestamp
        attr_lookup = {}
        for attr in attributions:
            ts = attr.get("timestamp", "")[:19]  # Truncate to second
            attr_lookup[ts] = attr.get("payload", {})

        # Combine fills with attributions
        trades = []
        for fill in fills:
            ts = fill.get("timestamp", "")[:19]
            payload = fill.get("payload", {})

            # Add attribution if available
            if ts in attr_lookup:
                payload["attribution"] = attr_lookup[ts]

            trades.append(payload)

        return trades

    def compute_adjustments(
        self,
        trades: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute parameter adjustments from attributed trades.

        Uses learning_weight to scale influence of each trade.
        Winning trades with low luck get higher weight.

        Args:
            trades: List of attributed trade records

        Returns:
            Proposed adjustments per parameter category
        """
        adjustments = {
            "signal_weights": {},
            "belief_thresholds": {},
            "decay_rates": {},
        }

        # Accumulators
        constraint_signals = {}  # constraint -> signal -> (weighted_delta_sum, weight_sum)
        constraint_threshold_deltas = {}  # constraint -> (weighted_delta_sum, weight_sum)

        for trade in trades:
            # Score the trade
            scores = score_post_trade(trade)
            learn_w = scores.learning_weight

            if learn_w < 0.1:
                continue  # Skip trades dominated by luck

            pnl = float(trade.get("pnl_usd", 0) or 0)
            attribution = trade.get("attribution", {})

            # Get context from the trade
            template_id = attribution.get("template_id")
            beliefs_at_entry = trade.get("beliefs_at_entry", {})
            signals_at_entry = trade.get("signals_at_entry", {})

            # Direction of adjustment based on outcome
            direction = 1.0 if pnl > 0 else -1.0
            magnitude = min(1.0, abs(pnl) / 50.0)  # Normalize by $50

            # For each constraint, update signal weight suggestions
            for constraint_id, belief_val in beliefs_at_entry.items():
                if constraint_id not in constraint_signals:
                    constraint_signals[constraint_id] = {}

                # Signals that contributed to this belief
                relevant_signals = self.params.signal_weights.get(constraint_id, {})

                for signal_name in relevant_signals:
                    signal_val = signals_at_entry.get(signal_name, 0)

                    if signal_name not in constraint_signals[constraint_id]:
                        constraint_signals[constraint_id][signal_name] = (0.0, 0.0)

                    old_sum, old_weight = constraint_signals[constraint_id][signal_name]

                    # If signal was aligned with outcome, reinforce
                    # If signal was misaligned, reduce weight
                    delta = direction * magnitude * signal_val * learn_w

                    constraint_signals[constraint_id][signal_name] = (
                        old_sum + delta,
                        old_weight + learn_w,
                    )

                # Threshold adjustment
                if constraint_id not in constraint_threshold_deltas:
                    constraint_threshold_deltas[constraint_id] = (0.0, 0.0)

                old_sum, old_weight = constraint_threshold_deltas[constraint_id]

                # If belief was high and won, keep threshold
                # If belief was low and won, lower threshold
                # If belief was high and lost, raise threshold
                threshold_delta = direction * (1.0 - belief_val) * magnitude * learn_w

                constraint_threshold_deltas[constraint_id] = (
                    old_sum + threshold_delta,
                    old_weight + learn_w,
                )

        # Compute weighted averages
        for constraint_id, signals in constraint_signals.items():
            if constraint_id not in adjustments["signal_weights"]:
                adjustments["signal_weights"][constraint_id] = {}

            for signal_name, (delta_sum, weight_sum) in signals.items():
                if weight_sum > 0:
                    avg_delta = delta_sum / weight_sum
                    # Scale to max_change
                    max_change = self.BOUNDS["signal_weights"]["max_change"]
                    clamped = max(-max_change, min(max_change, avg_delta * 0.1))
                    adjustments["signal_weights"][constraint_id][signal_name] = clamped

        for constraint_id, (delta_sum, weight_sum) in constraint_threshold_deltas.items():
            if weight_sum > 0:
                avg_delta = delta_sum / weight_sum
                max_change = self.BOUNDS["belief_thresholds"]["max_change"]
                clamped = max(-max_change, min(max_change, avg_delta * 0.01))
                adjustments["belief_thresholds"][constraint_id] = clamped

        return adjustments

    def apply_adjustments(
        self,
        adjustments: Dict[str, Dict[str, float]],
    ) -> Dict[str, Any]:
        """
        Apply bounded adjustments to current parameters.

        Args:
            adjustments: Proposed adjustments from compute_adjustments

        Returns:
            Dict of actual changes made
        """
        changes = {}

        # Apply signal weight adjustments
        for constraint_id, signals in adjustments.get("signal_weights", {}).items():
            if constraint_id not in self.params.signal_weights:
                continue

            for signal_name, delta in signals.items():
                if signal_name not in self.params.signal_weights[constraint_id]:
                    continue

                old_val = self.params.signal_weights[constraint_id][signal_name]
                new_val = old_val + delta

                # Apply bounds
                bounds = self.BOUNDS["signal_weights"]
                new_val = max(bounds["min"], min(bounds["max"], new_val))

                if new_val != old_val:
                    self.params.signal_weights[constraint_id][signal_name] = new_val
                    change_key = f"signal_weights.{constraint_id}.{signal_name}"
                    changes[change_key] = {"old": old_val, "new": new_val, "delta": new_val - old_val}

        # Apply belief threshold adjustments
        for constraint_id, delta in adjustments.get("belief_thresholds", {}).items():
            if constraint_id not in self.params.belief_thresholds:
                continue

            old_val = self.params.belief_thresholds[constraint_id]
            new_val = old_val + delta

            # Apply bounds
            bounds = self.BOUNDS["belief_thresholds"]
            new_val = max(bounds["min"], min(bounds["max"], new_val))

            if new_val != old_val:
                self.params.belief_thresholds[constraint_id] = new_val
                change_key = f"belief_thresholds.{constraint_id}"
                changes[change_key] = {"old": old_val, "new": new_val, "delta": new_val - old_val}

        # Apply decay rate adjustments
        for constraint_id, delta in adjustments.get("decay_rates", {}).items():
            if constraint_id not in self.params.decay_rates:
                continue

            old_val = self.params.decay_rates[constraint_id]
            new_val = old_val + delta

            bounds = self.BOUNDS["decay_rates"]
            new_val = max(bounds["min"], min(bounds["max"], new_val))

            if new_val != old_val:
                self.params.decay_rates[constraint_id] = new_val
                change_key = f"decay_rates.{constraint_id}"
                changes[change_key] = {"old": old_val, "new": new_val, "delta": new_val - old_val}

        return changes

    def learn_from_trade(
        self,
        trade_data: Dict[str, Any],
    ) -> EvolutionResult:
        """
        Learn from a single completed trade in real-time.

        This is the primary learning method - called after each trade.
        Uses smaller parameter increments than batch mode.

        Args:
            trade_data: Trade data including:
                - pnl_usd: Profit/loss in USD
                - beliefs_at_entry: Dict of constraint beliefs at entry
                - signals_at_entry: Dict of signal values at entry
                - template_id: Optional template used
                - entry_price, exit_price, qty, etc.

        Returns:
            EvolutionResult with details of what changed
        """
        now = datetime.now(ET)

        # Score the trade for learning weight
        scores = score_post_trade(trade_data)
        learn_w = scores.learning_weight

        if learn_w < 0.1:
            return EvolutionResult(
                success=False,
                trades_analyzed=1,
                parameters_updated=0,
                changes={},
                reason="LOW_LEARNING_WEIGHT (trade dominated by luck)",
                timestamp=now.isoformat(),
            )

        pnl = float(trade_data.get("pnl_usd", 0) or 0)
        beliefs_at_entry = trade_data.get("beliefs_at_entry", {})
        signals_at_entry = trade_data.get("signals_at_entry", {})

        # Direction and magnitude of adjustment
        direction = 1.0 if pnl > 0 else -1.0
        magnitude = min(1.0, abs(pnl) / 50.0)  # Normalize by $50

        changes = {}

        # Update signal weights for each constraint
        for constraint_id, belief_val in beliefs_at_entry.items():
            if constraint_id not in self.params.signal_weights:
                continue

            for signal_name in self.params.signal_weights[constraint_id]:
                signal_val = signals_at_entry.get(signal_name, 0)
                if signal_val == 0:
                    continue

                # Compute delta: reinforce if aligned with outcome
                base_delta = direction * magnitude * signal_val * learn_w * 0.1
                # Scale for real-time (smaller increments)
                max_change = self.BOUNDS["signal_weights"]["max_change"] * self.REALTIME_SCALE
                delta = max(-max_change, min(max_change, base_delta))

                old_val = self.params.signal_weights[constraint_id][signal_name]
                new_val = old_val + delta

                # Apply absolute bounds
                bounds = self.BOUNDS["signal_weights"]
                new_val = max(bounds["min"], min(bounds["max"], new_val))

                if abs(new_val - old_val) > 1e-6:
                    self.params.signal_weights[constraint_id][signal_name] = new_val
                    change_key = f"signal_weights.{constraint_id}.{signal_name}"
                    changes[change_key] = {"old": old_val, "new": new_val, "delta": new_val - old_val}

            # Update belief threshold for this constraint
            if constraint_id in self.params.belief_thresholds:
                # If won with low belief -> lower threshold
                # If lost with high belief -> raise threshold
                base_delta = direction * (1.0 - belief_val) * magnitude * learn_w * 0.01
                max_change = self.BOUNDS["belief_thresholds"]["max_change"] * self.REALTIME_SCALE
                delta = max(-max_change, min(max_change, base_delta))

                old_val = self.params.belief_thresholds[constraint_id]
                new_val = old_val + delta

                bounds = self.BOUNDS["belief_thresholds"]
                new_val = max(bounds["min"], min(bounds["max"], new_val))

                if abs(new_val - old_val) > 1e-6:
                    self.params.belief_thresholds[constraint_id] = new_val
                    change_key = f"belief_thresholds.{constraint_id}"
                    changes[change_key] = {"old": old_val, "new": new_val, "delta": new_val - old_val}

        # NEVER RIGHT CONSTITUTION: Decay parameters that weren't just updated
        confirmed_keys = set(changes.keys())
        decay_changes = self.decay_toward_neutral(confirmed_keys)
        changes.update(decay_changes)

        if changes:
            # Update metadata
            self.params.version += 1
            self.params.last_updated = now.isoformat()
            self.params.update_reason = f"REALTIME_LEARN_V{self.params.version}"

            # Persist
            self._save_params()

            # Log evolution event
            evolution_event = Event.make(
                "SYSTEM",
                now.isoformat(),
                "EVOLUTION_REALTIME",
                {
                    "version": self.params.version,
                    "pnl_usd": pnl,
                    "learning_weight": learn_w,
                    "changes": changes,
                    "decay_applied": len(decay_changes),  # Track neutral decay
                },
                sha256_hex(stable_json(asdict(self.params))),
            )
            self.event_store.append(evolution_event)

            logger.info(
                f"Learned from trade: pnl=${pnl:.2f}, {len(changes) - len(decay_changes)} learned, "
                f"{len(decay_changes)} decayed toward neutral"
            )

        return EvolutionResult(
            success=True,
            trades_analyzed=1,
            parameters_updated=len(changes),
            changes=changes,
            reason="REALTIME_LEARNED" if changes else "NO_CHANGES_NEEDED",
            timestamp=now.isoformat(),
        )

    def learn_from_trade_history(
        self,
        trade_history: Dict[str, Any],
        learning_rates: Optional[Dict[str, float]] = None,
    ) -> EvolutionResult:
        """
        Learn from complete trade history including in-trade decisions.

        This is the comprehensive learning method that uses:
        - Entry context (beliefs, signals)
        - In-trade evidence progression
        - State transitions and timing
        - Exit outcomes and attribution

        Args:
            trade_history: Complete history from InTradeManager.get_trade_history()
            learning_rates: Optional per-category rates from MetaLearner

        Returns:
            EvolutionResult with all changes
        """
        now = datetime.now(ET)

        if not trade_history:
            return EvolutionResult(
                success=False,
                trades_analyzed=0,
                parameters_updated=0,
                changes={},
                reason="EMPTY_HISTORY",
                timestamp=now.isoformat(),
            )

        context = trade_history.get("context", {})
        runtime = trade_history.get("runtime", {})
        bar_logs = trade_history.get("bar_logs", [])
        transitions = trade_history.get("transitions", [])

        # Get learning rates (from meta-learner or defaults)
        if learning_rates is None:
            learning_rates = {
                "signal_weights": self.REALTIME_SCALE,
                "belief_thresholds": self.REALTIME_SCALE,
                "in_trade_params": self.REALTIME_SCALE,
            }

        # Compute trade outcome
        entry_price = context.get("entry_price", 0)
        exit_price = runtime.get("exit_price", entry_price)
        direction = context.get("direction", 1)
        qty = context.get("qty_total", 1)
        R_points = context.get("R_points", 1)

        pnl_points = direction * (exit_price - entry_price)
        pnl_R = pnl_points / max(0.25, R_points)
        pnl_usd = pnl_points * qty * 5.0  # MES

        # Score for learning weight
        trade_data = {
            "pnl_usd": pnl_usd,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "mfe_points": runtime.get("mfe_points", 0),
            "mae_points": runtime.get("mae_points", 0),
        }
        scores = score_post_trade(trade_data)
        learn_w = scores.learning_weight

        if learn_w < 0.1:
            return EvolutionResult(
                success=False,
                trades_analyzed=1,
                parameters_updated=0,
                changes={},
                reason="LOW_LEARNING_WEIGHT",
                timestamp=now.isoformat(),
            )

        changes = {}

        # 1. Learn entry parameters (signal weights, belief thresholds)
        beliefs_at_entry = context.get("beliefs_at_entry", {})
        signals_at_entry = context.get("signals_at_entry", {})

        lr_signals = learning_rates.get("signal_weights", self.REALTIME_SCALE)
        lr_thresholds = learning_rates.get("belief_thresholds", self.REALTIME_SCALE)
        lr_in_trade = learning_rates.get("in_trade_params", self.REALTIME_SCALE)

        outcome_dir = 1.0 if pnl_usd > 0 else -1.0
        magnitude = min(1.0, abs(pnl_R))

        # Signal weights
        for constraint_id, belief_val in beliefs_at_entry.items():
            if constraint_id not in self.params.signal_weights:
                continue

            for signal_name in self.params.signal_weights[constraint_id]:
                signal_val = signals_at_entry.get(signal_name, 0)
                if signal_val == 0:
                    continue

                base_delta = outcome_dir * magnitude * signal_val * learn_w * 0.1
                max_change = self.BOUNDS["signal_weights"]["max_change"] * lr_signals
                delta = max(-max_change, min(max_change, base_delta))

                old_val = self.params.signal_weights[constraint_id][signal_name]
                new_val = old_val + delta
                bounds = self.BOUNDS["signal_weights"]
                new_val = max(bounds["min"], min(bounds["max"], new_val))

                if abs(new_val - old_val) > 1e-6:
                    self.params.signal_weights[constraint_id][signal_name] = new_val
                    key = f"signal_weights.{constraint_id}.{signal_name}"
                    changes[key] = {"old": old_val, "new": new_val, "delta": new_val - old_val}

        # 2. Learn in-trade parameters from trade history
        in_trade_changes = self._learn_in_trade_params(
            context, runtime, bar_logs, transitions,
            pnl_R, learn_w, lr_in_trade
        )
        changes.update(in_trade_changes)

        # 3. NEVER RIGHT CONSTITUTION: Decay parameters not just updated
        confirmed_keys = set(changes.keys())
        decay_changes = self.decay_toward_neutral(confirmed_keys)
        changes.update(decay_changes)

        # 4. Notify meta-learner of changes
        if self.meta_learner:
            for key in changes:
                old_val = changes[key]["old"]
                new_val = changes[key]["new"]
                self.meta_learner.record_param_change(key, old_val, new_val)

        if changes:
            self.params.version += 1
            self.params.last_updated = now.isoformat()
            self.params.update_reason = f"FULL_TRADE_LEARN_V{self.params.version}"
            self._save_params()

            evolution_event = Event.make(
                "SYSTEM",
                now.isoformat(),
                "EVOLUTION_FULL_TRADE",
                {
                    "version": self.params.version,
                    "pnl_usd": pnl_usd,
                    "pnl_R": pnl_R,
                    "learning_weight": learn_w,
                    "changes": changes,
                    "transitions": len(transitions),
                    "bars": len(bar_logs),
                },
                sha256_hex(stable_json(asdict(self.params))),
            )
            self.event_store.append(evolution_event)

            logger.info(
                f"Full trade learning: pnl={pnl_R:.2f}R, "
                f"{len(changes)} params updated"
            )

        return EvolutionResult(
            success=True,
            trades_analyzed=1,
            parameters_updated=len(changes),
            changes=changes,
            reason="FULL_TRADE_LEARNED" if changes else "NO_CHANGES_NEEDED",
            timestamp=now.isoformat(),
        )

    def _learn_in_trade_params(
        self,
        context: Dict[str, Any],
        runtime: Dict[str, Any],
        bar_logs: List[Dict[str, Any]],
        transitions: List[Dict[str, Any]],
        pnl_R: float,
        learn_w: float,
        lr_scale: float,
    ) -> Dict[str, Any]:
        """
        Learn in-trade management parameters from trade execution.

        Analyzes:
        - Protection timing and profitability
        - Scale execution quality
        - Runner performance
        - Kill switch accuracy

        Returns:
            Dict of parameter changes
        """
        changes = {}
        outcome_dir = 1.0 if pnl_R > 0 else -1.0
        magnitude = min(1.0, abs(pnl_R))

        # Get transition info
        did_protect = any(t["trigger"] == "PROTECT" for t in transitions)
        did_scale_t1 = runtime.get("T1_hit", False)
        did_scale_t2 = runtime.get("T2_hit", False)
        exit_reason = runtime.get("exit_reason", "")

        R_points = context.get("R_points", 1)
        entry_price = context.get("entry_price", 0)
        direction = context.get("direction", 1)

        # 1. Protection parameters
        if did_protect:
            # Find when protection happened
            protect_trans = next((t for t in transitions if t["trigger"] == "PROTECT"), None)
            if protect_trans:
                bars_to_protect = protect_trans.get("bars_in_trade", 0)

                # If we protected and won, reinforce current protection timing
                # If we protected and lost, maybe we should have protected sooner
                if pnl_R > 0:
                    # Good outcome - current k_protect worked
                    delta = learn_w * magnitude * 0.02 * lr_scale
                else:
                    # Lost - maybe protect sooner (lower k_protect)
                    delta = -learn_w * magnitude * 0.03 * lr_scale

                old_val = self.params.in_trade.k_protect
                new_val = old_val + delta
                bounds = self.IN_TRADE_BOUNDS["k_protect"]
                new_val = max(bounds["min"], min(bounds["max"], new_val))

                if abs(new_val - old_val) > 1e-6:
                    self.params.in_trade.k_protect = new_val
                    changes["in_trade.k_protect"] = {
                        "old": old_val, "new": new_val, "delta": new_val - old_val
                    }

        # 2. Scaling parameters - analyze T1/T2 timing
        if did_scale_t1:
            t1_price = runtime.get("T1_price", 0)
            exit_price = runtime.get("exit_price", entry_price)

            # Did we leave money on table by scaling at T1?
            if direction == 1:
                post_t1_move = exit_price - t1_price
            else:
                post_t1_move = t1_price - exit_price

            post_t1_R = post_t1_move / max(0.25, R_points)

            # If price went much higher after T1, maybe raise T1
            # If price reversed after T1, current T1 is good
            if post_t1_R > 0.5:
                # Scaled too early - raise T1
                delta = learn_w * min(0.3, post_t1_R * 0.1) * lr_scale
            elif post_t1_R < -0.5:
                # Good scaling - reinforce current T1
                delta = -learn_w * 0.02 * lr_scale
            else:
                delta = 0

            if delta != 0:
                old_val = self.params.in_trade.k_T1
                new_val = old_val + delta
                bounds = self.IN_TRADE_BOUNDS["k_T1"]
                new_val = max(bounds["min"], min(bounds["max"], new_val))

                if abs(new_val - old_val) > 1e-6:
                    self.params.in_trade.k_T1 = new_val
                    changes["in_trade.k_T1"] = {
                        "old": old_val, "new": new_val, "delta": new_val - old_val
                    }

        # 3. Runner trail parameter
        if exit_reason == "RUNNER_STOP" and did_scale_t2:
            # Analyze if trail was too tight or too loose
            mfe = runtime.get("mfe_points", 0)
            exit_price = runtime.get("exit_price", entry_price)

            if direction == 1:
                exit_R = (exit_price - entry_price) / max(0.25, R_points)
                mfe_R = mfe / max(0.25, R_points)
            else:
                exit_R = (entry_price - exit_price) / max(0.25, R_points)
                mfe_R = mfe / max(0.25, R_points)

            # How much did we give back?
            giveback_R = mfe_R - exit_R

            if giveback_R > 1.0:
                # Gave back a lot - tighten trail
                delta = -learn_w * min(0.05, giveback_R * 0.02) * lr_scale
            elif giveback_R < 0.3 and exit_R > 1.5:
                # Tight trail working well - maybe loosen slightly
                delta = learn_w * 0.01 * lr_scale
            else:
                delta = 0

            if delta != 0:
                old_val = self.params.in_trade.k_trail
                new_val = old_val + delta
                bounds = self.IN_TRADE_BOUNDS["k_trail"]
                new_val = max(bounds["min"], min(bounds["max"], new_val))

                if abs(new_val - old_val) > 1e-6:
                    self.params.in_trade.k_trail = new_val
                    changes["in_trade.k_trail"] = {
                        "old": old_val, "new": new_val, "delta": new_val - old_val
                    }

        # 4. Kill switch threshold
        if exit_reason == "KILL_SWITCH":
            # Evaluate if kill switch was correct
            if pnl_R < -0.5:
                # Kill switch saved us - reinforce current threshold
                delta = -learn_w * 0.01 * lr_scale  # Lower threshold = more sensitive
            elif pnl_R > 0.5:
                # Kill switch was false alarm - raise threshold
                delta = learn_w * 0.02 * lr_scale

                old_val = self.params.in_trade.theta_kill
                new_val = old_val + delta
                bounds = self.IN_TRADE_BOUNDS["theta_kill"]
                new_val = max(bounds["min"], min(bounds["max"], new_val))

                if abs(new_val - old_val) > 1e-6:
                    self.params.in_trade.theta_kill = new_val
                    changes["in_trade.theta_kill"] = {
                        "old": old_val, "new": new_val, "delta": new_val - old_val
                    }

        # 5. Evidence weights - analyze which evidence was predictive
        if bar_logs and len(bar_logs) > 5:
            # Compute average evidence components vs outcome
            avg_evidence = {
                "E_structure": 0,
                "E_pullback": 0,
                "E_momentum": 0,
                "E_signal": 0,
            }

            for log in bar_logs:
                ev = log.get("evidence", {})
                for key in avg_evidence:
                    avg_evidence[key] += ev.get(key, 0.5)

            n_bars = len(bar_logs)
            for key in avg_evidence:
                avg_evidence[key] /= n_bars

            # If trade won and a component was high, reinforce that weight
            # If trade lost and a component was high, reduce that weight
            weight_map = {
                "E_structure": "w_structure",
                "E_pullback": "w_pullback",
                "E_momentum": "w_momentum",
                "E_signal": "w_signal",
            }

            for ev_key, w_key in weight_map.items():
                ev_val = avg_evidence[ev_key]
                # How predictive was this component?
                contribution = (ev_val - 0.5) * 2  # -1 to 1

                # If high and won (or low and lost) -> reinforce
                # If high and lost (or low and won) -> reduce
                alignment = outcome_dir * contribution

                delta = learn_w * alignment * 0.01 * lr_scale

                old_val = getattr(self.params.in_trade, w_key)
                new_val = old_val + delta
                bounds = self.IN_TRADE_BOUNDS[w_key]
                new_val = max(bounds["min"], min(bounds["max"], new_val))

                if abs(new_val - old_val) > 1e-6:
                    setattr(self.params.in_trade, w_key, new_val)
                    changes[f"in_trade.{w_key}"] = {
                        "old": old_val, "new": new_val, "delta": new_val - old_val
                    }

            # Normalize weights to sum to 1
            self._normalize_evidence_weights()

        return changes

    def _normalize_evidence_weights(self) -> None:
        """Ensure evidence weights sum to 1.0."""
        total = (
            self.params.in_trade.w_structure +
            self.params.in_trade.w_pullback +
            self.params.in_trade.w_momentum +
            self.params.in_trade.w_signal
        )

        if total > 0 and abs(total - 1.0) > 0.001:
            self.params.in_trade.w_structure /= total
            self.params.in_trade.w_pullback /= total
            self.params.in_trade.w_momentum /= total
            self.params.in_trade.w_signal /= total

    def set_meta_learner(self, meta_learner) -> None:
        """Set meta-learner for learning rate adaptation."""
        self.meta_learner = meta_learner

    def decay_toward_neutral(self, confirmed_params: Optional[set] = None) -> Dict[str, Any]:
        """
        NEVER RIGHT CONSTITUTION: Decay parameters toward neutral defaults.

        Parameters that weren't used/confirmed in recent trades drift back
        toward their initial values. This prevents overconfidence buildup.

        Args:
            confirmed_params: Set of param keys that were just updated (don't decay these)

        Returns:
            Dict of parameters that were decayed
        """
        if confirmed_params is None:
            confirmed_params = set()

        changes = {}
        decay = self.NEUTRAL_DECAY_PER_TRADE

        # Default neutral values for belief thresholds
        default_thresholds = {"F1": 0.65, "F3": 0.60, "F4": 0.55, "F5": 0.50, "F6": 0.50}

        # Decay belief thresholds toward defaults
        for constraint_id, default_val in default_thresholds.items():
            if constraint_id not in self.params.belief_thresholds:
                continue

            key = f"belief_thresholds.{constraint_id}"
            if key in confirmed_params:
                continue  # Just updated, don't decay

            current = self.params.belief_thresholds[constraint_id]
            if abs(current - default_val) < 0.001:
                continue  # Already at neutral

            # Decay toward default
            if current > default_val:
                new_val = max(default_val, current - decay)
            else:
                new_val = min(default_val, current + decay)

            if new_val != current:
                self.params.belief_thresholds[constraint_id] = new_val
                changes[key] = {"old": current, "new": new_val, "delta": new_val - current}

        # Decay signal weights toward their defaults (0.25 as neutral)
        default_weight = 0.25
        for constraint_id, signals in self.params.signal_weights.items():
            for signal_name, current in list(signals.items()):
                key = f"signal_weights.{constraint_id}.{signal_name}"
                if key in confirmed_params:
                    continue

                if abs(current - default_weight) < 0.001:
                    continue

                if current > default_weight:
                    new_val = max(default_weight, current - decay)
                else:
                    new_val = min(default_weight, current + decay)

                if new_val != current:
                    self.params.signal_weights[constraint_id][signal_name] = new_val
                    changes[key] = {"old": current, "new": new_val, "delta": new_val - current}

        return changes

    def get_in_trade_params(self) -> InTradeParamsState:
        """Get current in-trade parameters for InTradeManager."""
        return self.params.in_trade

    def run_evolution(
        self,
        force: bool = False,
        dry_run: bool = False,
    ) -> EvolutionResult:
        """
        Run a full evolution cycle.

        Args:
            force: Override weekly cadence check
            dry_run: Compute adjustments but don't apply

        Returns:
            EvolutionResult with details of what changed
        """
        now = datetime.now(ET)

        # Check if it's the right time (Friday 16:05 ET)
        if not force:
            if now.weekday() != 4:  # Friday = 4
                return EvolutionResult(
                    success=False,
                    trades_analyzed=0,
                    parameters_updated=0,
                    changes={},
                    reason="NOT_FRIDAY",
                    timestamp=now.isoformat(),
                )

            if now.hour < 16 or (now.hour == 16 and now.minute < 5):
                return EvolutionResult(
                    success=False,
                    trades_analyzed=0,
                    parameters_updated=0,
                    changes={},
                    reason="SESSION_NOT_CLOSED",
                    timestamp=now.isoformat(),
                )

        # Get attributed trades from the past week
        trades = self.get_attributed_trades()

        if len(trades) < self.MIN_TRADES_FOR_UPDATE:
            return EvolutionResult(
                success=False,
                trades_analyzed=len(trades),
                parameters_updated=0,
                changes={},
                reason=f"INSUFFICIENT_TRADES ({len(trades)} < {self.MIN_TRADES_FOR_UPDATE})",
                timestamp=now.isoformat(),
            )

        # Compute adjustments
        adjustments = self.compute_adjustments(trades)

        if dry_run:
            return EvolutionResult(
                success=True,
                trades_analyzed=len(trades),
                parameters_updated=0,
                changes={"proposed": adjustments},
                reason="DRY_RUN",
                timestamp=now.isoformat(),
            )

        # Apply adjustments
        changes = self.apply_adjustments(adjustments)

        if changes:
            # Update metadata
            self.params.version += 1
            self.params.last_updated = now.isoformat()
            self.params.update_reason = f"EVOLUTION_V{self.params.version}"

            # Persist
            self._save_params()

            # Log evolution event
            evolution_event = Event.make(
                "SYSTEM",
                now.isoformat(),
                "EVOLUTION_UPDATE",
                {
                    "version": self.params.version,
                    "trades_analyzed": len(trades),
                    "changes": changes,
                },
                sha256_hex(stable_json(asdict(self.params))),
            )
            self.event_store.append(evolution_event)

        return EvolutionResult(
            success=True,
            trades_analyzed=len(trades),
            parameters_updated=len(changes),
            changes=changes,
            reason="SUCCESS" if changes else "NO_CHANGES_NEEDED",
            timestamp=now.isoformat(),
        )

    def get_current_params(self) -> ParameterState:
        """Get current parameter state."""
        return self.params

    def get_param_value(self, category: str, key: str, subkey: Optional[str] = None) -> Any:
        """
        Get a specific parameter value.

        Args:
            category: "signal_weights", "belief_thresholds", etc.
            key: Constraint ID or template ID
            subkey: Signal name (for signal_weights)

        Returns:
            Parameter value or None
        """
        category_data = getattr(self.params, category, {})

        if subkey:
            return category_data.get(key, {}).get(subkey)
        return category_data.get(key)


def create_evolution_engine(
    db_path: str = "data/events.sqlite",
    contracts_path: str = "src/trading_bot/contracts",
) -> EvolutionEngine:
    """
    Factory function to create an evolution engine.

    Args:
        db_path: Path to SQLite event store
        contracts_path: Path to contract YAML files

    Returns:
        Configured EvolutionEngine
    """
    event_store = EventStore(db_path)
    return EvolutionEngine(event_store, contracts_path)
