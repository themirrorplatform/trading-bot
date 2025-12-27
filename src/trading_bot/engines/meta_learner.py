"""
Meta-Learner - Learning from the learning process.

Implements:
- Learning rate adaptation based on recent performance
- Regime detection and regime-specific parameters
- Parameter drift detection and reversion
- Confidence tracking for each parameter
- Emergency freeze on excessive drawdown

The meta-learner doesn't change parameters directly - it adjusts
HOW the EvolutionEngine learns.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from zoneinfo import ZoneInfo

from trading_bot.log.event_store import EventStore
from trading_bot.core.types import Event, stable_json, sha256_hex

logger = logging.getLogger(__name__)
ET = ZoneInfo("America/New_York")


@dataclass
class LearningRateState:
    """Current learning rate configuration."""
    # Base rate (default 0.05, range 0.01-0.15)
    base_rate: float = 0.05

    # Per-category multipliers
    signal_weights_mult: float = 1.0
    belief_thresholds_mult: float = 1.0
    in_trade_params_mult: float = 1.0

    # Regime-specific adjustments
    high_vol_mult: float = 0.5   # Slower learning in high vol
    low_vol_mult: float = 1.2    # Faster learning in low vol

    # Meta state
    frozen: bool = False
    freeze_reason: Optional[str] = None
    freeze_until: Optional[str] = None


@dataclass
class ParameterConfidence:
    """
    Confidence tracking for a parameter.

    NEVER RIGHT CONSTITUTION:
    - Confidence is CAPPED at 0.75 (never believe we're fully right)
    - Confidence decays toward neutral (0.5) when no confirming evidence
    - Symmetric updates: losses reduce confidence as fast as wins increase it
    """
    param_key: str
    n_updates: int = 0
    n_positive_outcomes: int = 0
    n_negative_outcomes: int = 0  # Track losses symmetrically
    last_values: List[float] = field(default_factory=list)
    last_outcomes: List[float] = field(default_factory=list)  # PnL after change
    confidence: float = 0.5  # 0 = no confidence, 0.75 = max confidence (never 1.0!)
    bars_since_confirming: int = 0  # Decay when no confirmation

    # Never Right constants
    MAX_CONFIDENCE = 0.75
    NEUTRAL = 0.5
    DECAY_PER_UPDATE = 0.02

    def update(self, new_value: float, outcome_pnl: float) -> None:
        """Update confidence after observing outcome - SYMMETRIC."""
        self.n_updates += 1

        # SYMMETRIC tracking: count wins AND losses equally
        if outcome_pnl > 0:
            self.n_positive_outcomes += 1
            self.bars_since_confirming = 0  # Reset decay timer
        else:
            self.n_negative_outcomes += 1
            # Losses also reset decay - we're getting information

        self.last_values.append(new_value)
        self.last_outcomes.append(outcome_pnl)

        # Keep last 20
        if len(self.last_values) > 20:
            self.last_values = self.last_values[-20:]
            self.last_outcomes = self.last_outcomes[-20:]

        # Compute confidence - SYMMETRIC with hard cap
        if self.n_updates >= 5:
            win_rate = self.n_positive_outcomes / self.n_updates
            # SYMMETRIC: win_rate directly maps to confidence offset from neutral
            # win_rate=0.5 -> confidence=0.5 (neutral)
            # win_rate=1.0 -> confidence=0.75 (capped max)
            # win_rate=0.0 -> confidence=0.25 (symmetric minimum)
            confidence_offset = (win_rate - 0.5) * 0.5  # Range: -0.25 to +0.25
            self.confidence = self.NEUTRAL + confidence_offset
        else:
            self.confidence = self.NEUTRAL  # Not enough data

        # HARD CAP: Never believe we're fully right
        self.confidence = min(self.MAX_CONFIDENCE, max(1.0 - self.MAX_CONFIDENCE, self.confidence))

    def decay_toward_neutral(self) -> None:
        """Decay confidence toward neutral when no confirming evidence."""
        self.bars_since_confirming += 1
        # Exponential decay toward 0.5
        decay = self.DECAY_PER_UPDATE
        if self.confidence > self.NEUTRAL:
            self.confidence = max(self.NEUTRAL, self.confidence - decay)
        elif self.confidence < self.NEUTRAL:
            self.confidence = min(self.NEUTRAL, self.confidence + decay)


@dataclass
class RegimeState:
    """Current market regime detection."""
    # Volatility regime
    vol_regime: str = "NORMAL"  # LOW, NORMAL, HIGH
    sigma_norm_20: float = 1.0

    # Trend regime
    trend_regime: str = "NEUTRAL"  # TRENDING, NEUTRAL, RANGING

    # Recent performance in regime
    trades_in_regime: int = 0
    pnl_in_regime: float = 0.0
    win_rate_in_regime: float = 0.0

    # Regime change tracking
    last_regime_change: Optional[str] = None
    bars_since_change: int = 0


@dataclass
class MetaLearnerState:
    """Persistent state for meta-learner."""
    # Learning rates
    learning_rates: LearningRateState = field(default_factory=LearningRateState)

    # Parameter confidence
    param_confidence: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Regime
    regime: RegimeState = field(default_factory=RegimeState)

    # Performance tracking
    rolling_sharpe_20: float = 0.0
    rolling_pnl_20: List[float] = field(default_factory=list)
    drawdown_current: float = 0.0
    drawdown_max: float = 0.0
    equity_peak: float = 0.0

    # Learning effectiveness
    param_changes_last_20: int = 0
    outcomes_after_changes: List[float] = field(default_factory=list)
    learning_effectiveness: float = 0.5  # Are changes helping?

    # Version
    version: int = 1
    last_updated: Optional[str] = None


class MetaLearner:
    """
    Meta-learning layer that adjusts how the bot learns.

    Key responsibilities:
    1. Track learning effectiveness
    2. Adjust learning rates based on performance
    3. Detect and adapt to regime changes
    4. Freeze learning if things go wrong
    5. Track confidence in each parameter

    Usage:
        meta = MetaLearner(event_store)

        # Before evolution
        rates = meta.get_learning_rates(regime_info)

        # After evolution
        meta.record_param_change(param_key, old_val, new_val)

        # After trade
        meta.record_trade_outcome(pnl, regime_info)

        # Periodic
        meta.update_meta_state()
    """

    # Thresholds
    DRAWDOWN_FREEZE_THRESHOLD = 0.15    # Freeze learning at 15% DD
    SHARPE_SLOW_THRESHOLD = 0.0         # Slow learning if Sharpe < 0
    MIN_TRADES_FOR_META = 10            # Min trades before meta-learning kicks in
    REGIME_CHANGE_DECAY_MULT = 0.3      # Faster decay after regime change

    # NEVER RIGHT CONSTITUTION - Symmetric learning invariants
    MAX_PARAM_CONFIDENCE = 0.75         # Never believe we're fully right
    NEUTRAL_DECAY_RATE = 0.02           # Decay toward neutral per update
    # NO success-accelerated learning - removed SHARPE_FAST_THRESHOLD

    def __init__(
        self,
        event_store: EventStore,
        state_path: str = "data/meta_learner_state.json",
    ):
        self.event_store = event_store
        self.state_path = Path(state_path)
        self.state = self._load_state()

    def _load_state(self) -> MetaLearnerState:
        """Load persisted state."""
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                # Reconstruct nested dataclasses
                if "learning_rates" in data:
                    data["learning_rates"] = LearningRateState(**data["learning_rates"])
                if "regime" in data:
                    data["regime"] = RegimeState(**data["regime"])
                if "param_confidence" in data:
                    # Convert dicts back to ParameterConfidence
                    for k, v in data["param_confidence"].items():
                        if isinstance(v, dict):
                            data["param_confidence"][k] = v  # Keep as dict for simplicity
                return MetaLearnerState(**{
                    k: v for k, v in data.items()
                    if k in MetaLearnerState.__dataclass_fields__
                })
            except Exception as e:
                logger.warning(f"Could not load meta state: {e}")
        return MetaLearnerState()

    def _save_state(self) -> None:
        """Persist current state."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        # Convert dataclasses to dicts
        state_dict = {
            "learning_rates": asdict(self.state.learning_rates),
            "param_confidence": self.state.param_confidence,
            "regime": asdict(self.state.regime),
            "rolling_sharpe_20": self.state.rolling_sharpe_20,
            "rolling_pnl_20": self.state.rolling_pnl_20,
            "drawdown_current": self.state.drawdown_current,
            "drawdown_max": self.state.drawdown_max,
            "equity_peak": self.state.equity_peak,
            "param_changes_last_20": self.state.param_changes_last_20,
            "outcomes_after_changes": self.state.outcomes_after_changes,
            "learning_effectiveness": self.state.learning_effectiveness,
            "version": self.state.version,
            "last_updated": self.state.last_updated,
        }
        with open(self.state_path, "w") as f:
            json.dump(state_dict, f, indent=2)

    def get_learning_rates(
        self,
        sigma_norm: float = 1.0,
    ) -> Dict[str, float]:
        """
        Get current learning rates adjusted for regime.

        Args:
            sigma_norm: Current normalized volatility

        Returns:
            Dict of category -> learning rate
        """
        lr = self.state.learning_rates

        # Check if frozen
        if lr.frozen:
            return {
                "signal_weights": 0.0,
                "belief_thresholds": 0.0,
                "in_trade_params": 0.0,
            }

        # Base rate
        base = lr.base_rate

        # Volatility adjustment
        if sigma_norm > 1.5:
            vol_mult = lr.high_vol_mult
        elif sigma_norm < 0.7:
            vol_mult = lr.low_vol_mult
        else:
            vol_mult = 1.0

        # Performance adjustment - SYMMETRIC LEARNING
        # Never Right Constitution: unlearn from losses AS FAST as we learn from wins
        # No success acceleration - that breeds overconfidence
        perf_mult = 1.0
        if self.state.rolling_sharpe_20 < self.SHARPE_SLOW_THRESHOLD:
            perf_mult = 0.5  # Slow down when losing (to avoid thrashing)
        # REMOVED: success acceleration (perf_mult = 1.5 when winning)
        # The danger is asymmetric confidence accumulation, not learning speed

        # Regime change adjustment
        if self.state.regime.bars_since_change < 20:
            # Recently changed regime - be cautious
            regime_mult = self.REGIME_CHANGE_DECAY_MULT
        else:
            regime_mult = 1.0

        # Combine
        effective_base = base * vol_mult * perf_mult * regime_mult

        return {
            "signal_weights": effective_base * lr.signal_weights_mult,
            "belief_thresholds": effective_base * lr.belief_thresholds_mult,
            "in_trade_params": effective_base * lr.in_trade_params_mult,
        }

    def should_learn(self) -> Tuple[bool, str]:
        """
        Check if learning should proceed.

        Returns:
            (should_learn, reason)
        """
        lr = self.state.learning_rates

        if lr.frozen:
            return False, lr.freeze_reason or "FROZEN"

        if self.state.drawdown_current > self.DRAWDOWN_FREEZE_THRESHOLD:
            return False, f"DRAWDOWN_{self.state.drawdown_current:.1%}"

        return True, "OK"

    def record_param_change(
        self,
        param_key: str,
        old_value: float,
        new_value: float,
    ) -> None:
        """
        Record that a parameter was changed.

        Args:
            param_key: e.g., "signal_weights.F1.vwap_z"
            old_value: Previous value
            new_value: New value
        """
        self.state.param_changes_last_20 += 1

        # Initialize confidence tracking if needed
        if param_key not in self.state.param_confidence:
            self.state.param_confidence[param_key] = {
                "n_updates": 0,
                "n_positive_outcomes": 0,
                "last_values": [],
                "last_outcomes": [],
                "confidence": 0.5,
                "pending_value": new_value,
            }
        else:
            self.state.param_confidence[param_key]["pending_value"] = new_value

    def record_trade_outcome(
        self,
        pnl_usd: float,
        sigma_norm: float = 1.0,
        trend_strength: float = 0.0,
    ) -> None:
        """
        Record a trade outcome for meta-learning.

        Args:
            pnl_usd: Trade P&L in dollars
            sigma_norm: Volatility at trade time
            trend_strength: Trend strength at trade time
        """
        # Update rolling PnL
        self.state.rolling_pnl_20.append(pnl_usd)
        if len(self.state.rolling_pnl_20) > 20:
            self.state.rolling_pnl_20 = self.state.rolling_pnl_20[-20:]

        # Update outcomes for pending param changes
        for param_key, conf in self.state.param_confidence.items():
            if "pending_value" in conf:
                conf["last_outcomes"].append(pnl_usd)
                conf["n_updates"] = conf.get("n_updates", 0) + 1
                if pnl_usd > 0:
                    conf["n_positive_outcomes"] = conf.get("n_positive_outcomes", 0) + 1
                # Keep last 20
                if len(conf["last_outcomes"]) > 20:
                    conf["last_outcomes"] = conf["last_outcomes"][-20:]
                # Remove pending
                del conf["pending_value"]

        # Update regime tracking
        self.state.regime.trades_in_regime += 1
        self.state.regime.pnl_in_regime += pnl_usd
        if self.state.regime.trades_in_regime > 0:
            wins = sum(1 for p in self.state.rolling_pnl_20 if p > 0)
            self.state.regime.win_rate_in_regime = wins / len(self.state.rolling_pnl_20)

        # Detect regime change
        self._update_regime(sigma_norm, trend_strength)

        self._save_state()

    def _update_regime(self, sigma_norm: float, trend_strength: float) -> None:
        """Update regime detection."""
        old_vol_regime = self.state.regime.vol_regime

        # Update volatility regime
        # Use 20-bar EMA of sigma_norm
        alpha = 0.1
        self.state.regime.sigma_norm_20 = (
            alpha * sigma_norm +
            (1 - alpha) * self.state.regime.sigma_norm_20
        )

        if self.state.regime.sigma_norm_20 > 1.5:
            new_vol_regime = "HIGH"
        elif self.state.regime.sigma_norm_20 < 0.7:
            new_vol_regime = "LOW"
        else:
            new_vol_regime = "NORMAL"

        self.state.regime.vol_regime = new_vol_regime

        # Trend regime
        if abs(trend_strength) > 0.5:
            self.state.regime.trend_regime = "TRENDING"
        elif abs(trend_strength) < 0.2:
            self.state.regime.trend_regime = "RANGING"
        else:
            self.state.regime.trend_regime = "NEUTRAL"

        # Check for regime change
        if new_vol_regime != old_vol_regime:
            self.state.regime.last_regime_change = datetime.now(ET).isoformat()
            self.state.regime.bars_since_change = 0
            self.state.regime.trades_in_regime = 0
            self.state.regime.pnl_in_regime = 0.0
            logger.info(f"Regime change: {old_vol_regime} -> {new_vol_regime}")
        else:
            self.state.regime.bars_since_change += 1

    def update_performance_metrics(self, equity: float) -> None:
        """
        Update performance metrics from equity.

        Args:
            equity: Current account equity
        """
        # Update equity peak
        if equity > self.state.equity_peak:
            self.state.equity_peak = equity

        # Update drawdown
        if self.state.equity_peak > 0:
            self.state.drawdown_current = (self.state.equity_peak - equity) / self.state.equity_peak
            self.state.drawdown_max = max(self.state.drawdown_max, self.state.drawdown_current)

        # Check for freeze
        if self.state.drawdown_current > self.DRAWDOWN_FREEZE_THRESHOLD:
            if not self.state.learning_rates.frozen:
                self._freeze_learning(f"DRAWDOWN_{self.state.drawdown_current:.1%}")

        # Rolling Sharpe (simplified)
        if len(self.state.rolling_pnl_20) >= 5:
            pnls = self.state.rolling_pnl_20
            mean_pnl = sum(pnls) / len(pnls)
            if len(pnls) > 1:
                variance = sum((p - mean_pnl) ** 2 for p in pnls) / (len(pnls) - 1)
                std_pnl = variance ** 0.5
                if std_pnl > 0:
                    self.state.rolling_sharpe_20 = mean_pnl / std_pnl * (252 ** 0.5)  # Annualized
                else:
                    self.state.rolling_sharpe_20 = 0.0
            else:
                self.state.rolling_sharpe_20 = 0.0

        self._save_state()

    def _freeze_learning(self, reason: str, duration_hours: int = 24) -> None:
        """Freeze all learning temporarily."""
        now = datetime.now(ET)
        until = now + timedelta(hours=duration_hours)

        self.state.learning_rates.frozen = True
        self.state.learning_rates.freeze_reason = reason
        self.state.learning_rates.freeze_until = until.isoformat()

        logger.warning(f"Learning frozen: {reason} until {until}")

        # Log event
        event = Event.make(
            "SYSTEM",
            now.isoformat(),
            "META_LEARNING_FREEZE",
            {
                "reason": reason,
                "until": until.isoformat(),
                "drawdown": self.state.drawdown_current,
                "sharpe": self.state.rolling_sharpe_20,
            },
            sha256_hex(stable_json({"frozen": True, "reason": reason})),
        )
        self.event_store.append(event)

    def unfreeze_learning(self) -> None:
        """Manually unfreeze learning."""
        self.state.learning_rates.frozen = False
        self.state.learning_rates.freeze_reason = None
        self.state.learning_rates.freeze_until = None
        self._save_state()
        logger.info("Learning unfrozen")

    def check_auto_unfreeze(self) -> None:
        """Check if freeze should auto-expire."""
        if not self.state.learning_rates.frozen:
            return

        if self.state.learning_rates.freeze_until:
            until = datetime.fromisoformat(self.state.learning_rates.freeze_until)
            if datetime.now(ET) > until:
                self.unfreeze_learning()

    def compute_learning_effectiveness(self) -> float:
        """
        Compute how effective recent learning has been.

        Returns:
            Effectiveness score 0-1 (1 = changes are helping)
        """
        if len(self.state.outcomes_after_changes) < 5:
            return 0.5  # Not enough data

        # Compare outcomes after param changes to overall
        post_change = self.state.outcomes_after_changes[-10:]
        overall = self.state.rolling_pnl_20

        if not overall:
            return 0.5

        avg_post_change = sum(post_change) / len(post_change)
        avg_overall = sum(overall) / len(overall)

        # If post-change avg > overall avg, learning is helping
        if avg_overall != 0:
            ratio = avg_post_change / abs(avg_overall)
            effectiveness = 1 / (1 + math.exp(-ratio))  # Sigmoid
        else:
            effectiveness = 0.5 if avg_post_change >= 0 else 0.3

        self.state.learning_effectiveness = effectiveness
        return effectiveness

    def get_param_confidence(self, param_key: str) -> float:
        """Get confidence score for a parameter."""
        if param_key in self.state.param_confidence:
            return self.state.param_confidence[param_key].get("confidence", 0.5)
        return 0.5

    def decay_all_confidences(self) -> None:
        """
        NEVER RIGHT CONSTITUTION: Decay all parameter confidences toward neutral.

        Call periodically (e.g., after each trade or daily) to ensure
        the system never breeds confidence in being right.
        """
        for param_key, conf_data in self.state.param_confidence.items():
            current = conf_data.get("confidence", 0.5)
            # Decay toward neutral (0.5)
            if current > 0.5:
                new_conf = max(0.5, current - self.NEUTRAL_DECAY_RATE)
            elif current < 0.5:
                new_conf = min(0.5, current + self.NEUTRAL_DECAY_RATE)
            else:
                new_conf = current

            # Enforce hard cap
            new_conf = min(self.MAX_PARAM_CONFIDENCE, new_conf)
            conf_data["confidence"] = new_conf

    def adjust_learning_rates(self) -> None:
        """
        Periodically adjust learning rates based on meta-metrics.

        Call this after every N trades or daily.

        NEVER RIGHT CONSTITUTION:
        - No success acceleration
        - Confidence capped at 0.75
        - All confidences decay toward neutral
        """
        effectiveness = self.compute_learning_effectiveness()
        lr = self.state.learning_rates

        # NEVER RIGHT: Decay all confidences toward neutral first
        self.decay_all_confidences()

        # Adjust base rate based on effectiveness - BUT symmetrically
        if effectiveness > 0.6:
            # Learning is helping - increase slightly
            lr.base_rate = min(0.15, lr.base_rate * 1.1)
        elif effectiveness < 0.4:
            # Learning is hurting - decrease SYMMETRICALLY (same magnitude)
            lr.base_rate = max(0.01, lr.base_rate * 0.9)  # Was 0.8, now 0.9 for symmetry

        # Adjust per-category based on confidence (capped at 0.75)
        categories = ["signal_weights", "belief_thresholds", "in_trade_params"]
        for cat in categories:
            # Find params in this category
            cat_confidences = [
                min(self.MAX_PARAM_CONFIDENCE, self.state.param_confidence[k].get("confidence", 0.5))
                for k in self.state.param_confidence
                if k.startswith(cat)
            ]
            if cat_confidences:
                avg_conf = sum(cat_confidences) / len(cat_confidences)
                # Higher confidence = faster learning, BUT capped
                # With max confidence of 0.75, max multiplier is 1.25 (not 1.5)
                mult_key = f"{cat}_mult"
                if hasattr(lr, mult_key):
                    current = getattr(lr, mult_key)
                    new_mult = 0.5 + avg_conf  # Range 0.5 to 1.25 (capped)
                    setattr(lr, mult_key, 0.9 * current + 0.1 * new_mult)

        self.state.version += 1
        self.state.last_updated = datetime.now(ET).isoformat()
        self._save_state()

        logger.info(
            f"Meta-learning update: effectiveness={effectiveness:.2f}, "
            f"base_rate={lr.base_rate:.3f}"
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current meta-learner status."""
        return {
            "frozen": self.state.learning_rates.frozen,
            "freeze_reason": self.state.learning_rates.freeze_reason,
            "base_rate": self.state.learning_rates.base_rate,
            "vol_regime": self.state.regime.vol_regime,
            "trend_regime": self.state.regime.trend_regime,
            "sharpe_20": self.state.rolling_sharpe_20,
            "drawdown": self.state.drawdown_current,
            "effectiveness": self.state.learning_effectiveness,
            "version": self.state.version,
        }
