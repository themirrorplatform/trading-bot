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
    """

    # Default bounds from constitution (weekly batch mode)
    BOUNDS = {
        "signal_weights": {"min": 0.0, "max": 1.5, "max_change": 0.05},
        "belief_thresholds": {"min": 0.50, "max": 0.95, "max_change": 0.01},
        "decay_rates": {"min": 0.90, "max": 0.995, "max_change": 0.005},
        "template_stop_buffers": {"min": -2, "max": 2, "max_change": 1},
        "template_time_stops": {"min": 10, "max": 60, "max_change": 2},
    }

    # Real-time learning uses smaller increments (1/20th of weekly for ~20 trades/week)
    REALTIME_SCALE = 0.05

    MIN_TRADES_FOR_UPDATE = 10

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
                },
                sha256_hex(stable_json(asdict(self.params))),
            )
            self.event_store.append(evolution_event)

            logger.info(f"Learned from trade: pnl=${pnl:.2f}, {len(changes)} params updated")

        return EvolutionResult(
            success=True,
            trades_analyzed=1,
            parameters_updated=len(changes),
            changes=changes,
            reason="REALTIME_LEARNED" if changes else "NO_CHANGES_NEEDED",
            timestamp=now.isoformat(),
        )

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
