"""
In-Trade Manager - Real-time learning and management during active trades.

Implements:
- State machine (ENTERED → PROTECTED → SCALED_1 → SCALED_2 → RUNNER)
- Evidence tracking (continuation vs reversal)
- Adaptive trailing based on belief strength
- Kill switch on reversal evidence
- Context capture for post-trade learning

All beliefs update every bar. Parameters are frozen during trade.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from zoneinfo import ZoneInfo

from trading_bot.engines.belief_v2 import BeliefState

logger = logging.getLogger(__name__)
ET = ZoneInfo("America/New_York")


class InTradeState(Enum):
    """Trade lifecycle states."""
    WATCHING = 0      # No position
    ENTERED = 1       # Just entered, full risk at initial stop
    PROTECTED = 2     # Stop moved to reduce risk
    SCALED_1 = 3      # First target hit, partial exit
    SCALED_2 = 4      # Second target hit, runner remains
    RUNNER = 5        # Trailing the remaining position
    FLAT = 6          # Position closed


class ExitReason(Enum):
    """Why a trade was closed."""
    STOP = "STOP"
    TARGET = "TARGET"
    RUNNER_STOP = "RUNNER_STOP"
    KILL_SWITCH = "KILL_SWITCH"
    TIME_STOP = "TIME_STOP"
    MANUAL = "MANUAL"


@dataclass
class InTradeParams:
    """
    Parameters for in-trade management.

    These are frozen at trade entry and evolved post-trade.
    """
    # Protection
    k_protect: float = 1.0           # Protect after +1R
    k_lock: float = 0.25             # Lock +0.25R when protecting
    min_bars_before_protect: int = 3
    theta_protect: float = 0.20      # Min smoothed evidence to protect

    # Scaling (R multiples)
    k_T1: float = 1.0                # First target at 1R
    k_T2: float = 2.0                # Second target at 2R
    k_scale1_lock: float = 0.5       # Lock 0.5R after T1
    k_scale2_lock: float = 1.0       # Lock 1.0R after T2

    # Runner
    k_trail: float = 0.75            # Trail buffer in ATR
    theta_runner_entry: float = 0.40 # Min evidence to start runner
    sigma_norm_max: float = 1.5      # Max volatility for runner
    stale_bars_max: int = 15         # Max bars without new extreme

    # Kill switch
    theta_kill: float = 0.70         # Exit if E_rev exceeds this

    # Tightening
    theta_tight: float = 0.25        # Tighten trail below this evidence
    theta_recover: float = 0.35      # Recover from tight above this
    max_tight_bars: int = 5          # Time stop in tight mode

    # Evidence smoothing
    beta_smooth: float = 0.30        # EMA alpha for evidence

    # Transition throttling
    min_bars_between_transitions: int = 2


@dataclass
class SwingPoint:
    """A confirmed swing high or low."""
    price: float
    bar_index: int
    confirmed_at: int


@dataclass
class InTradeContext:
    """
    Complete context for a trade, frozen at entry.

    Used for post-trade learning attribution.
    """
    # Entry info
    trade_id: str
    symbol: str
    direction: int  # +1 long, -1 short
    entry_price: float
    entry_time: str
    initial_stop: float
    qty_total: int

    # Lot allocation
    qty_A: int  # For T1
    qty_B: int  # For T2
    qty_C: int  # Runner

    # Template used
    template_id: Optional[str] = None

    # Entry beliefs (frozen snapshot)
    beliefs_at_entry: Dict[str, float] = field(default_factory=dict)
    signals_at_entry: Dict[str, float] = field(default_factory=dict)

    # Quality scores at entry
    dvs_at_entry: float = 1.0
    eqs_at_entry: float = 1.0
    euc_at_entry: float = 0.0

    # Parameters frozen at entry
    params: InTradeParams = field(default_factory=InTradeParams)

    # Risk
    R_points: float = 0.0  # |entry - stop|, always positive


@dataclass
class InTradeRuntime:
    """
    Mutable state that changes during trade.

    Beliefs update here. Parameters don't.
    """
    state: InTradeState = InTradeState.WATCHING

    # Position tracking
    qty_remaining: int = 0
    qty_A_remaining: int = 0
    qty_B_remaining: int = 0
    qty_C_remaining: int = 0

    # Stop management
    stop_current: float = 0.0

    # Targets
    T1: float = 0.0
    T2: float = 0.0
    T1_hit: bool = False
    T2_hit: bool = False
    T1_price: Optional[float] = None
    T2_price: Optional[float] = None
    T1_time: Optional[str] = None
    T2_time: Optional[str] = None

    # Evidence (updates every bar)
    E_structure: float = 0.5
    E_pullback: float = 0.5
    E_momentum: float = 0.5
    E_signal: float = 0.5
    E_cont: float = 0.5
    E_break: float = 0.0
    E_mom_rev: float = 0.0
    E_vol_against: float = 0.0
    E_rev: float = 0.0
    E_net: float = 0.0
    E_net_smooth: float = 0.0

    # Counters
    bars_in_trade: int = 0
    bars_in_state: int = 0
    bars_since_transition: int = 999
    bars_since_new_extreme: int = 0

    # Excursions
    mfe_points: float = 0.0
    mae_points: float = 0.0
    best_price: float = 0.0
    worst_price: float = 0.0
    last_extreme_price: float = 0.0

    # Swings (confirmed only)
    swing_highs: List[SwingPoint] = field(default_factory=list)
    swing_lows: List[SwingPoint] = field(default_factory=list)

    # ATR tracking
    atr: float = 0.0
    atr_history: List[float] = field(default_factory=list)
    sigma_norm: float = 1.0

    # Bar history for swing detection
    bar_highs: List[float] = field(default_factory=list)
    bar_lows: List[float] = field(default_factory=list)
    bar_closes: List[float] = field(default_factory=list)

    # Exit info
    exit_reason: Optional[ExitReason] = None
    exit_price: Optional[float] = None
    exit_time: Optional[str] = None


@dataclass
class BarSnapshot:
    """A single bar of price data."""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class TradeAction:
    """Action to take from in-trade manager."""
    action_type: str  # "NONE", "MODIFY_STOP", "SCALE_EXIT", "FULL_EXIT"
    new_stop: Optional[float] = None
    exit_qty: int = 0
    exit_reason: Optional[ExitReason] = None
    exit_price: Optional[float] = None


class InTradeManager:
    """
    Manages a single trade from entry to exit.

    Key responsibilities:
    1. Track state machine progression
    2. Update beliefs/evidence every bar
    3. Manage stop movements (monotone only)
    4. Trigger scales at targets
    5. Implement kill switch
    6. Capture full context for post-trade learning

    Usage:
        manager = InTradeManager()
        manager.start_trade(context)
        for bar in bars:
            action = manager.on_bar(bar, beliefs, signals, atr)
            # Execute action
        # When flat, get full history for learning
        history = manager.get_trade_history()
    """

    # Evidence weights (must sum to 1.0)
    W_STRUCTURE = 0.30
    W_PULLBACK = 0.25
    W_MOMENTUM = 0.25
    W_SIGNAL = 0.20

    # Reversal weights
    W_BREAK = 0.50
    W_MOM_REV = 0.30
    W_VOL_AGAINST = 0.20

    def __init__(self):
        self.ctx: Optional[InTradeContext] = None
        self.rt = InTradeRuntime()
        self.bar_logs: List[Dict[str, Any]] = []
        self.transition_logs: List[Dict[str, Any]] = []
        self.prev_close: Optional[float] = None

    def is_active(self) -> bool:
        """Check if currently in a trade."""
        return self.ctx is not None and self.rt.state not in (
            InTradeState.WATCHING, InTradeState.FLAT
        )

    def start_trade(self, context: InTradeContext) -> None:
        """
        Initialize a new trade.

        Args:
            context: Trade context with entry info and frozen parameters
        """
        self.ctx = context
        self.rt = InTradeRuntime()
        self.bar_logs = []
        self.transition_logs = []
        self.prev_close = None

        # Initialize runtime from context
        self.rt.state = InTradeState.ENTERED
        self.rt.stop_current = context.initial_stop
        self.rt.qty_remaining = context.qty_total
        self.rt.qty_A_remaining = context.qty_A
        self.rt.qty_B_remaining = context.qty_B
        self.rt.qty_C_remaining = context.qty_C

        # Compute R (always positive)
        R = abs(context.entry_price - context.initial_stop)
        R = max(0.25, R)  # Min 1 tick

        # Store in context (it's frozen but we set R here)
        object.__setattr__(context, 'R_points', R)

        # Compute targets
        self.rt.T1 = context.entry_price + context.direction * context.params.k_T1 * R
        self.rt.T2 = context.entry_price + context.direction * context.params.k_T2 * R

        # Initialize excursions
        self.rt.best_price = context.entry_price
        self.rt.worst_price = context.entry_price
        self.rt.last_extreme_price = context.entry_price

        logger.info(
            f"Trade started: {context.symbol} {'+' if context.direction > 0 else '-'}"
            f"{context.qty_total} @ {context.entry_price}, "
            f"stop={context.initial_stop}, T1={self.rt.T1:.2f}, T2={self.rt.T2:.2f}"
        )

        self._log_transition("ENTERED", None, None)

    def on_bar(
        self,
        bar: BarSnapshot,
        beliefs: Dict[str, BeliefState],
        signals: Dict[str, float],
        atr: float,
    ) -> TradeAction:
        """
        Process a new bar and return action.

        Args:
            bar: Current bar data
            beliefs: Current belief states from BeliefEngineV2
            signals: Current signal values from SignalEngineV2
            atr: Current ATR value

        Returns:
            TradeAction indicating what to do
        """
        if not self.is_active():
            return TradeAction(action_type="NONE")

        assert self.ctx is not None
        ctx = self.ctx
        params = ctx.params

        # Update ATR
        self.rt.atr = max(0.5, atr)
        self.rt.atr_history.append(self.rt.atr)
        if len(self.rt.atr_history) >= 50:
            self.rt.sigma_norm = self.rt.atr / (sum(self.rt.atr_history[-50:]) / 50)

        # Update bar history for swings
        self.rt.bar_highs.append(bar.high)
        self.rt.bar_lows.append(bar.low)
        self.rt.bar_closes.append(bar.close)

        # Detect confirmed swings
        self._detect_swings()

        # Update excursions
        self._update_excursions(bar)

        # Increment counters
        self.rt.bars_in_trade += 1
        self.rt.bars_in_state += 1
        self.rt.bars_since_transition += 1

        # Compute evidence from beliefs
        self._compute_evidence(bar, beliefs, signals)

        # Check for stop hit (before any other logic)
        if self._stop_hit(bar):
            return self._exit_trade(bar, ExitReason.STOP, self.rt.stop_current)

        # Check kill switch
        if self.rt.E_rev > params.theta_kill:
            self._log_transition("KILL_SWITCH", bar, self.rt.E_net_smooth)
            return self._exit_trade(bar, ExitReason.KILL_SWITCH, bar.close)

        # Handle scaling (target hits)
        scale_action = self._handle_scaling(bar)
        if scale_action.action_type != "NONE":
            return scale_action

        # State transitions
        action = self._handle_transitions(bar)

        # Log bar
        self._log_bar(bar, beliefs, signals)

        self.prev_close = bar.close
        return action

    def _compute_evidence(
        self,
        bar: BarSnapshot,
        beliefs: Dict[str, BeliefState],
        signals: Dict[str, float],
    ) -> None:
        """
        Compute continuation and reversal evidence from V2 beliefs.

        Maps F1-F6 constraints to evidence scores.
        """
        assert self.ctx is not None
        ctx = self.ctx
        params = ctx.params

        # Structure evidence from F1 (trend) and F3 (breakout)
        f1 = beliefs.get("F1")
        f3 = beliefs.get("F3")
        if f1 and f3:
            self.rt.E_structure = 0.6 * f1.effective_likelihood + 0.4 * f3.effective_likelihood
        elif f1:
            self.rt.E_structure = f1.effective_likelihood
        else:
            self.rt.E_structure = 0.5

        # Pullback evidence from excursions
        mfe = self.rt.mfe_points
        mae = self.rt.mae_points
        if mfe > 0.25:
            pullback_ratio = mae / mfe
            self.rt.E_pullback = max(0.0, 1.0 - 2.0 * pullback_ratio)
        else:
            self.rt.E_pullback = 0.5

        # Momentum from F4
        f4 = beliefs.get("F4")
        if f4:
            self.rt.E_momentum = f4.effective_likelihood
        else:
            # Fallback: ATR-normalized drift
            if self.rt.atr > 0:
                drift = ctx.direction * (bar.close - ctx.entry_price)
                drift_norm = drift / self.rt.atr
                self.rt.E_momentum = self._sigmoid(2.0 * drift_norm)
            else:
                self.rt.E_momentum = 0.5

        # Signal persistence from signal average
        if signals:
            # Average of direction-relevant signals
            sig_vals = [v for v in signals.values() if isinstance(v, (int, float))]
            if sig_vals:
                avg_signal = sum(sig_vals) / len(sig_vals)
                # Map to 0-1 via sigmoid
                self.rt.E_signal = self._sigmoid(1.5 * ctx.direction * avg_signal)
            else:
                self.rt.E_signal = 0.5
        else:
            self.rt.E_signal = 0.5

        # Aggregate continuation evidence
        self.rt.E_cont = (
            self.W_STRUCTURE * self.rt.E_structure +
            self.W_PULLBACK * self.rt.E_pullback +
            self.W_MOMENTUM * self.rt.E_momentum +
            self.W_SIGNAL * self.rt.E_signal
        )
        self.rt.E_cont = max(0.0, min(1.0, self.rt.E_cont))

        # Reversal evidence
        # Structure break: price closes below recent swing low (long) / above swing high (short)
        self.rt.E_break = 0.0
        if ctx.direction == +1 and self.rt.swing_lows:
            recent_sl = self.rt.swing_lows[-1].price
            if bar.close < recent_sl:
                self.rt.E_break = 1.0
        elif ctx.direction == -1 and self.rt.swing_highs:
            recent_sh = self.rt.swing_highs[-1].price
            if bar.close > recent_sh:
                self.rt.E_break = 1.0

        # Momentum reversal
        if self.rt.atr > 0:
            drift = ctx.direction * (bar.close - ctx.entry_price)
            drift_norm = drift / self.rt.atr
            self.rt.E_mom_rev = self._sigmoid(-2.0 * drift_norm)
        else:
            self.rt.E_mom_rev = 0.5

        # Volatility against position
        delta_p = ctx.direction * (bar.close - bar.open)
        if delta_p < 0 and self.rt.sigma_norm > 1.3:
            self.rt.E_vol_against = min(1.0, abs(delta_p) / max(0.5, self.rt.atr))
        else:
            self.rt.E_vol_against = 0.0

        # Aggregate reversal evidence
        self.rt.E_rev = (
            self.W_BREAK * self.rt.E_break +
            self.W_MOM_REV * self.rt.E_mom_rev +
            self.W_VOL_AGAINST * self.rt.E_vol_against
        )
        self.rt.E_rev = max(0.0, min(1.0, self.rt.E_rev))

        # Net evidence with staleness decay
        stale_decay = max(0.0, 1.0 - self.rt.bars_since_new_extreme / max(1, params.stale_bars_max))
        E_cont_adj = self.rt.E_cont * stale_decay
        self.rt.E_net = E_cont_adj - self.rt.E_rev
        self.rt.E_net = max(-1.0, min(1.0, self.rt.E_net))

        # Smooth evidence
        self.rt.E_net_smooth = (
            params.beta_smooth * self.rt.E_net +
            (1 - params.beta_smooth) * self.rt.E_net_smooth
        )
        self.rt.E_net_smooth = max(-1.0, min(1.0, self.rt.E_net_smooth))

    def _detect_swings(self) -> None:
        """Detect confirmed swing highs/lows with 2-bar delay."""
        n_confirm = 2
        if len(self.rt.bar_highs) < (2 * n_confirm + 1):
            return

        mid_idx = len(self.rt.bar_highs) - 1 - n_confirm

        # Check for swing high
        mid_high = self.rt.bar_highs[mid_idx]
        is_swing_high = True
        for i in range(mid_idx - n_confirm, mid_idx + n_confirm + 1):
            if i != mid_idx and self.rt.bar_highs[i] >= mid_high:
                is_swing_high = False
                break
        if is_swing_high:
            self.rt.swing_highs.append(SwingPoint(
                price=mid_high,
                bar_index=mid_idx,
                confirmed_at=self.rt.bars_in_trade
            ))

        # Check for swing low
        mid_low = self.rt.bar_lows[mid_idx]
        is_swing_low = True
        for i in range(mid_idx - n_confirm, mid_idx + n_confirm + 1):
            if i != mid_idx and self.rt.bar_lows[i] <= mid_low:
                is_swing_low = False
                break
        if is_swing_low:
            self.rt.swing_lows.append(SwingPoint(
                price=mid_low,
                bar_index=mid_idx,
                confirmed_at=self.rt.bars_in_trade
            ))

    def _update_excursions(self, bar: BarSnapshot) -> None:
        """Update MFE, MAE, and extreme tracking."""
        assert self.ctx is not None
        ctx = self.ctx

        # Update best/worst
        if ctx.direction == +1:
            if bar.high > self.rt.best_price:
                self.rt.best_price = bar.high
                self.rt.bars_since_new_extreme = 0
                self.rt.last_extreme_price = bar.high
            else:
                self.rt.bars_since_new_extreme += 1
            self.rt.worst_price = min(self.rt.worst_price, bar.low)
        else:
            if bar.low < self.rt.best_price:
                self.rt.best_price = bar.low
                self.rt.bars_since_new_extreme = 0
                self.rt.last_extreme_price = bar.low
            else:
                self.rt.bars_since_new_extreme += 1
            self.rt.worst_price = max(self.rt.worst_price, bar.high)

        # MFE/MAE in points
        self.rt.mfe_points = ctx.direction * (self.rt.best_price - ctx.entry_price)
        self.rt.mae_points = -ctx.direction * (self.rt.worst_price - ctx.entry_price)
        self.rt.mfe_points = max(0.0, self.rt.mfe_points)
        self.rt.mae_points = max(0.0, self.rt.mae_points)

    def _stop_hit(self, bar: BarSnapshot) -> bool:
        """Check if stop was hit."""
        assert self.ctx is not None
        if self.ctx.direction == +1:
            return bar.low <= self.rt.stop_current or bar.open <= self.rt.stop_current
        else:
            return bar.high >= self.rt.stop_current or bar.open >= self.rt.stop_current

    def _handle_scaling(self, bar: BarSnapshot) -> TradeAction:
        """Handle target hits and scaling."""
        assert self.ctx is not None
        ctx = self.ctx
        params = ctx.params

        # Check T1
        if not self.rt.T1_hit and self.rt.qty_A_remaining > 0:
            t1_hit = (
                (ctx.direction == +1 and bar.high >= self.rt.T1) or
                (ctx.direction == -1 and bar.low <= self.rt.T1)
            )
            if t1_hit:
                self.rt.T1_hit = True
                self.rt.T1_price = self.rt.T1
                self.rt.T1_time = bar.timestamp
                qty_exit = self.rt.qty_A_remaining
                self.rt.qty_A_remaining = 0
                self.rt.qty_remaining -= qty_exit

                # Tighten stop after T1
                new_stop = self._compute_scale_stop(params.k_scale1_lock)

                self._log_transition("SCALE_T1", bar, self.rt.E_net_smooth)

                if self.rt.state in (InTradeState.ENTERED, InTradeState.PROTECTED):
                    self._transition_to(InTradeState.SCALED_1, bar)

                return TradeAction(
                    action_type="SCALE_EXIT",
                    exit_qty=qty_exit,
                    exit_reason=ExitReason.TARGET,
                    exit_price=self.rt.T1,
                    new_stop=new_stop,
                )

        # Check T2
        if self.rt.T1_hit and not self.rt.T2_hit and self.rt.qty_B_remaining > 0:
            t2_hit = (
                (ctx.direction == +1 and bar.high >= self.rt.T2) or
                (ctx.direction == -1 and bar.low <= self.rt.T2)
            )
            if t2_hit:
                self.rt.T2_hit = True
                self.rt.T2_price = self.rt.T2
                self.rt.T2_time = bar.timestamp
                qty_exit = self.rt.qty_B_remaining
                self.rt.qty_B_remaining = 0
                self.rt.qty_remaining -= qty_exit

                # Tighten stop after T2
                new_stop = self._compute_scale_stop(params.k_scale2_lock)

                self._log_transition("SCALE_T2", bar, self.rt.E_net_smooth)

                self._transition_to(InTradeState.SCALED_2, bar)

                return TradeAction(
                    action_type="SCALE_EXIT",
                    exit_qty=qty_exit,
                    exit_reason=ExitReason.TARGET,
                    exit_price=self.rt.T2,
                    new_stop=new_stop,
                )

        return TradeAction(action_type="NONE")

    def _compute_scale_stop(self, k_lock: float) -> float:
        """Compute new stop after scaling, locking in profit."""
        assert self.ctx is not None
        ctx = self.ctx
        R = ctx.R_points

        lock_stop = ctx.entry_price + ctx.direction * k_lock * R

        if ctx.direction == +1:
            new_stop = max(self.rt.stop_current, lock_stop)
        else:
            new_stop = min(self.rt.stop_current, lock_stop)

        self.rt.stop_current = new_stop
        return new_stop

    def _handle_transitions(self, bar: BarSnapshot) -> TradeAction:
        """Handle state machine transitions."""
        assert self.ctx is not None
        ctx = self.ctx
        params = ctx.params

        can_transition = self.rt.bars_since_transition >= params.min_bars_between_transitions
        action = TradeAction(action_type="NONE")

        # ENTERED → PROTECTED
        if self.rt.state == InTradeState.ENTERED and can_transition:
            if self._should_protect(bar):
                new_stop = self._compute_protection_stop()
                self._transition_to(InTradeState.PROTECTED, bar)
                self._log_transition("PROTECT", bar, self.rt.E_net_smooth)
                action = TradeAction(action_type="MODIFY_STOP", new_stop=new_stop)

        # SCALED_2 → RUNNER (or exit if not eligible)
        if self.rt.state == InTradeState.SCALED_2 and can_transition:
            if self._runner_eligible():
                self._transition_to(InTradeState.RUNNER, bar)
                self._log_transition("RUNNER_START", bar, self.rt.E_net_smooth)
            else:
                # Not eligible for runner, exit remaining
                return self._exit_trade(bar, ExitReason.TARGET, bar.close)

        # RUNNER state: update trail
        if self.rt.state == InTradeState.RUNNER:
            new_stop = self._compute_runner_trail()
            if self._stop_improved(new_stop):
                self.rt.stop_current = new_stop
                action = TradeAction(action_type="MODIFY_STOP", new_stop=new_stop)

            # Check for tight mode
            if self.rt.E_net_smooth < params.theta_tight:
                self._log_transition("RUNNER_TIGHT", bar, self.rt.E_net_smooth)
                # Could implement RUNNER_TIGHT state here
                # For now, just tighten the trail more aggressively

        return action

    def _should_protect(self, bar: BarSnapshot) -> bool:
        """Check if we should move to protected state."""
        assert self.ctx is not None
        ctx = self.ctx
        params = ctx.params

        if self.rt.bars_in_trade < params.min_bars_before_protect:
            return False

        # R current
        R_cur = ctx.direction * (bar.close - ctx.entry_price) / ctx.R_points
        if R_cur < params.k_protect:
            return False

        if self.rt.E_net_smooth < params.theta_protect:
            return False

        return True

    def _compute_protection_stop(self) -> float:
        """Compute protection stop: max(current, breakeven+friction, lock)."""
        assert self.ctx is not None
        ctx = self.ctx
        params = ctx.params

        # Breakeven with friction
        friction_per_contract = 4.0  # Estimated round-trip cost
        qty = max(1, self.rt.qty_remaining)
        friction_points = friction_per_contract / (qty * 5.0)  # $5/point for MES
        be = ctx.entry_price + ctx.direction * friction_points

        # Lock profit
        lock = ctx.entry_price + ctx.direction * params.k_lock * ctx.R_points

        if ctx.direction == +1:
            new_stop = max(self.rt.stop_current, be, lock)
        else:
            new_stop = min(self.rt.stop_current, be, lock)

        self.rt.stop_current = new_stop
        return new_stop

    def _runner_eligible(self) -> bool:
        """Check if runner mode is allowed."""
        assert self.ctx is not None
        params = self.ctx.params

        if self.rt.sigma_norm > params.sigma_norm_max:
            return False
        if self.rt.E_net_smooth < params.theta_runner_entry:
            return False
        if self.rt.qty_remaining <= 0:
            return False

        return True

    def _compute_runner_trail(self) -> float:
        """Compute runner trailing stop."""
        assert self.ctx is not None
        ctx = self.ctx
        params = ctx.params

        # Adaptive buffer based on evidence
        E_01 = (self.rt.E_net_smooth + 1) / 2  # Map -1..1 to 0..1
        k_adapt = params.k_trail * (0.5 + 0.5 * E_01)
        buffer = k_adapt * self.rt.atr

        if ctx.direction == +1:
            # Trail off highest swing low
            if self.rt.swing_lows:
                base = max(sl.price for sl in self.rt.swing_lows)
            else:
                base = self.rt.best_price - self.rt.atr
            trail = base - buffer
        else:
            # Trail off lowest swing high
            if self.rt.swing_highs:
                base = min(sh.price for sh in self.rt.swing_highs)
            else:
                base = self.rt.best_price + self.rt.atr
            trail = base + buffer

        return trail

    def _stop_improved(self, new_stop: float) -> bool:
        """Check if new stop is better (more profit locked)."""
        assert self.ctx is not None
        if self.ctx.direction == +1:
            return new_stop > self.rt.stop_current
        else:
            return new_stop < self.rt.stop_current

    def _transition_to(self, new_state: InTradeState, bar: BarSnapshot) -> None:
        """Transition to a new state."""
        self.rt.state = new_state
        self.rt.bars_in_state = 0
        self.rt.bars_since_transition = 0

    def _exit_trade(
        self,
        bar: BarSnapshot,
        reason: ExitReason,
        price: float,
    ) -> TradeAction:
        """Exit the trade completely."""
        qty = self.rt.qty_remaining
        self.rt.qty_remaining = 0
        self.rt.qty_A_remaining = 0
        self.rt.qty_B_remaining = 0
        self.rt.qty_C_remaining = 0
        self.rt.exit_reason = reason
        self.rt.exit_price = price
        self.rt.exit_time = bar.timestamp
        self.rt.state = InTradeState.FLAT

        self._log_transition(f"EXIT_{reason.value}", bar, self.rt.E_net_smooth)

        logger.info(f"Trade exited: {reason.value} @ {price}, qty={qty}")

        return TradeAction(
            action_type="FULL_EXIT",
            exit_qty=qty,
            exit_reason=reason,
            exit_price=price,
        )

    def _log_transition(
        self,
        trigger: str,
        bar: Optional[BarSnapshot],
        evidence: Optional[float],
    ) -> None:
        """Log a state transition."""
        self.transition_logs.append({
            "trigger": trigger,
            "state": self.rt.state.name,
            "timestamp": bar.timestamp if bar else datetime.now(ET).isoformat(),
            "stop_current": self.rt.stop_current,
            "qty_remaining": self.rt.qty_remaining,
            "E_net_smooth": evidence or self.rt.E_net_smooth,
            "bars_in_trade": self.rt.bars_in_trade,
        })

    def _log_bar(
        self,
        bar: BarSnapshot,
        beliefs: Dict[str, BeliefState],
        signals: Dict[str, float],
    ) -> None:
        """Log bar-level data for learning."""
        self.bar_logs.append({
            "timestamp": bar.timestamp,
            "bar": {
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            },
            "state": self.rt.state.name,
            "evidence": {
                "E_structure": self.rt.E_structure,
                "E_pullback": self.rt.E_pullback,
                "E_momentum": self.rt.E_momentum,
                "E_signal": self.rt.E_signal,
                "E_cont": self.rt.E_cont,
                "E_break": self.rt.E_break,
                "E_rev": self.rt.E_rev,
                "E_net": self.rt.E_net,
                "E_net_smooth": self.rt.E_net_smooth,
            },
            "stop_current": self.rt.stop_current,
            "qty_remaining": self.rt.qty_remaining,
            "mfe_points": self.rt.mfe_points,
            "mae_points": self.rt.mae_points,
            "atr": self.rt.atr,
            "sigma_norm": self.rt.sigma_norm,
            "bars_since_new_extreme": self.rt.bars_since_new_extreme,
        })

    def get_trade_history(self) -> Dict[str, Any]:
        """
        Get complete trade history for post-trade learning.

        Returns:
            Dict with entry context, runtime state, bar logs, transitions
        """
        if self.ctx is None:
            return {}

        return {
            "context": asdict(self.ctx),
            "runtime": {
                "state": self.rt.state.name,
                "exit_reason": self.rt.exit_reason.value if self.rt.exit_reason else None,
                "exit_price": self.rt.exit_price,
                "exit_time": self.rt.exit_time,
                "T1_hit": self.rt.T1_hit,
                "T1_price": self.rt.T1_price,
                "T2_hit": self.rt.T2_hit,
                "T2_price": self.rt.T2_price,
                "mfe_points": self.rt.mfe_points,
                "mae_points": self.rt.mae_points,
                "bars_in_trade": self.rt.bars_in_trade,
                "swing_highs": [asdict(sh) for sh in self.rt.swing_highs],
                "swing_lows": [asdict(sl) for sl in self.rt.swing_lows],
            },
            "bar_logs": self.bar_logs,
            "transitions": self.transition_logs,
        }

    @staticmethod
    def _sigmoid(x: float) -> float:
        """Stable sigmoid function."""
        if x >= 0:
            z = __import__('math').exp(-x)
            return 1 / (1 + z)
        z = __import__('math').exp(x)
        return z / (1 + z)
