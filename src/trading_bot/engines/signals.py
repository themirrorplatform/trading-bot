"""
Signal computations for MES survival bot.

All signals align with signals.yaml and session.yaml contracts.
Uses America/New_York timezone, [start, end) semantics.
VWAP resets at 09:30 RTH open using typical price (H+L+C)/3.
ATR uses Wilder smoothing, not SMA.
"""

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional, Dict, Any
from decimal import Decimal
from collections import deque
from zoneinfo import ZoneInfo


# America/New_York timezone for all session logic
ET = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class SessionPhase:
    """
    Session phase per session.yaml v1.0.1.
    Phases use [start, end) semantics (start inclusive, end exclusive).
    """
    phase_code: int
    name: str
    description: str


class SignalEngine:
    """
    Computes technical signals per signals.yaml contract.
    """
    
    def __init__(self, tick_size: Decimal = Decimal("0.25")):
        self.tick_size = tick_size
        
        # VWAP state (resets at 09:30 RTH, uses typical price)
        self._vwap_sum_pv: Decimal = Decimal("0")
        self._vwap_sum_v: int = 0
        self._vwap_session_started: bool = False
        self._last_rth_date: Optional[str] = None
        
        # ATR(14) Wilder smoothing
        self._atr14: Optional[Decimal] = None
        self._atr14_warmup: int = 0
        
        # ATR(30) Wilder smoothing
        self._atr30: Optional[Decimal] = None
        self._atr30_warmup: int = 0
        
        # Prior close for TR calculation
        self._prior_close: Optional[Decimal] = None
    
    def get_session_phase(self, current_time: datetime) -> SessionPhase:
        """
        Determine session phase per session.yaml v1.0.1.
        
        Phases (start inclusive, end exclusive):
        0: PRE_MARKET (before 09:30)
        1: OPENING (09:30 <= t < 10:30)
        2: MID_MORNING (10:30 <= t < 11:30)
        3: LUNCH (11:30 <= t < 13:30) - no-trade
        4: AFTERNOON (13:30 <= t < 15:00)
        5: CLOSE (15:00 <= t < 16:00)
        6: POST_RTH (>= 16:00)
        7: UNKNOWN (fail-closed)
        """
        # Ensure timezone-aware
        if current_time.tzinfo is None:
            # Assume ET if naive
            current_time = current_time.replace(tzinfo=ET)
        elif current_time.tzinfo != ET:
            # Convert to ET
            current_time = current_time.astimezone(ET)
        
        t = current_time.time()
        
        # [start, end) semantics
        if t < time(9, 30):
            return SessionPhase(0, "PRE_MARKET", "Before RTH open")
        elif t < time(10, 30):
            return SessionPhase(1, "OPENING", "Opening hour 09:30-10:30")
        elif t < time(11, 30):
            return SessionPhase(2, "MID_MORNING", "Mid-morning 10:30-11:30")
        elif t < time(13, 30):
            return SessionPhase(3, "LUNCH", "Lunch void 11:30-13:30")
        elif t < time(15, 0):
            return SessionPhase(4, "AFTERNOON", "Afternoon 13:30-15:00")
        elif t < time(16, 0):
            return SessionPhase(5, "CLOSE", "Close phase 15:00-16:00")
        else:
            return SessionPhase(6, "POST_RTH", "After 16:00")
    
    def update_vwap(
        self, 
        timestamp: datetime, 
        high: Decimal, 
        low: Decimal, 
        close: Decimal, 
        volume: int
    ) -> Optional[Decimal]:
        """
        Update VWAP using typical price (H+L+C)/3.
        Resets at 09:30 RTH open per signals.yaml contract.
        Only RTH bars contribute (09:30 <= t < 16:00).
        
        Returns current VWAP or None if before first RTH bar.
        """
        # Ensure timezone-aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=ET)
        elif timestamp.tzinfo != ET:
            timestamp = timestamp.astimezone(ET)
        
        t = timestamp.time()
        rth_date = timestamp.strftime("%Y-%m-%d")
        
        # Check if RTH bar (09:30 <= t < 16:00)
        is_rth = time(9, 30) <= t < time(16, 0)
        
        if not is_rth:
            # Non-RTH bar: return None, don't accumulate
            return None
        
        # Reset at 09:30 on new trading day
        if self._last_rth_date != rth_date:
            self._vwap_sum_pv = Decimal("0")
            self._vwap_sum_v = 0
            self._vwap_session_started = True
            self._last_rth_date = rth_date
        
        # Typical price: (H+L+C)/3
        typical_price = (high + low + close) / Decimal("3")
        
        # Accumulate typical_price * volume
        self._vwap_sum_pv += typical_price * Decimal(volume)
        self._vwap_sum_v += volume
        
        if self._vwap_sum_v == 0:
            return None
        
        return self._vwap_sum_pv / Decimal(self._vwap_sum_v)
    
    def compute_true_range(self, high: Decimal, low: Decimal, prior_close: Optional[Decimal]) -> Decimal:
        """
        Compute true range: max(H-L, |H-PC|, |L-PC|).
        
        If no prior_close, use H-L.
        """
        if prior_close is None:
            return high - low
        
        return max(
            high - low,
            abs(high - prior_close),
            abs(low - prior_close)
        )
    
    def update_atrs(self, high: Decimal, low: Decimal, close: Decimal) -> Dict[str, Optional[Decimal]]:
        """
        Update ATR(14) and ATR(30) using the SAME True Range computed from the PRIOR close.
        This prevents call-order bugs and guarantees consistency.
        
        Returns:
          {"tr": Decimal, "atr14": Optional[Decimal], "atr30": Optional[Decimal]}
        """
        prior_close = self._prior_close
        tr = self.compute_true_range(high, low, prior_close)

        # --- ATR14 ---
        atr14_out: Optional[Decimal] = None
        if self._atr14 is None:
            self._atr14_warmup += 1
            if not hasattr(self, "_tr_accumulator14"):
                self._tr_accumulator14 = Decimal("0")
            if self._atr14_warmup < 14:
                self._tr_accumulator14 += tr
            else:
                # first ATR14 = mean of first 14 TRs
                self._atr14 = (self._tr_accumulator14 + tr) / Decimal("14")
                atr14_out = self._atr14
        else:
            self._atr14 = (self._atr14 * Decimal("13") + tr) / Decimal("14")
            atr14_out = self._atr14

        # --- ATR30 ---
        atr30_out: Optional[Decimal] = None
        if self._atr30 is None:
            self._atr30_warmup += 1
            if not hasattr(self, "_tr_accumulator30"):
                self._tr_accumulator30 = Decimal("0")
            if self._atr30_warmup < 30:
                self._tr_accumulator30 += tr
            else:
                self._atr30 = (self._tr_accumulator30 + tr) / Decimal("30")
                atr30_out = self._atr30
        else:
            self._atr30 = (self._atr30 * Decimal("29") + tr) / Decimal("30")
            atr30_out = self._atr30

        # Update prior close only AFTER computing TR for this bar
        self._prior_close = close

        return {"tr": tr, "atr14": atr14_out, "atr30": atr30_out}
    
    def compute_spread_ticks(self, bid: Optional[Decimal], ask: Optional[Decimal]) -> Optional[int]:
        """
        Compute bid-ask spread in ticks per signals.yaml contract.
        
        Returns None if:
        - bid or ask missing
        - bid >= ask (invalid)
        - spread not exact multiple of tick_size
        """
        if bid is None or ask is None:
            return None
        
        if ask <= bid:
            # Invalid spread
            return None
        
        spread_price = ask - bid

        # Enforce exact tick multiple via quantization (fail-closed)
        spread_ticks_raw = spread_price / self.tick_size
        if spread_ticks_raw != spread_ticks_raw.to_integral_value():
            return None
        return int(spread_ticks_raw)
    
    def reset_session_state(self):
        """Reset all session-dependent state (for testing or session boundaries)."""
        self._vwap_sum_pv = Decimal("0")
        self._vwap_sum_v = 0
        self._vwap_session_started = False
        self._last_rth_date = None
        self._atr14 = None
        self._atr14_warmup = 0
        self._atr30 = None
        self._atr30_warmup = 0
        self._prior_close = None
        if hasattr(self, '_tr_accumulator14'):
            del self._tr_accumulator14
        if hasattr(self, '_tr_accumulator30'):
            del self._tr_accumulator30


# Legacy stub for compatibility
def compute_signals(bar_payload: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy stub - use SignalEngine class directly."""
    raise NotImplementedError("Use SignalEngine class directly")
