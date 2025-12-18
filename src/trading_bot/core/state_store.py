from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal
from zoneinfo import ZoneInfo


ET = ZoneInfo("America/New_York")


@dataclass
class RiskState:
    kill_switch_active: bool = False
    daily_pnl: Decimal = Decimal("0")
    consecutive_losses: int = 0
    trades_today: int = 0
    last_entry_time: Optional[datetime] = None


class StateStore:
    """In-memory risk/state store for v1 with simple day-boundary handling.

    Persisting to disk/DB can be added via `EventStore` consumption in v2.
    """

    def __init__(self):
        self._risk_state = RiskState()
        self._current_day: Optional[str] = None

    def get_risk_state(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        ts = (now or datetime.now(ET))
        ts = ts if ts.tzinfo else ts.replace(tzinfo=ET)
        day = ts.strftime("%Y-%m-%d")
        # Day-boundary rollover: reset trades_today and consecutive_losses at new local day
        if self._current_day is None:
            self._current_day = day
        elif self._current_day != day:
            self._current_day = day
            self._risk_state.trades_today = 0
            self._risk_state.consecutive_losses = 0
            self._risk_state.daily_pnl = Decimal("0")

        return {
            "kill_switch_active": self._risk_state.kill_switch_active,
            "daily_pnl": self._risk_state.daily_pnl,
            "consecutive_losses": self._risk_state.consecutive_losses,
            "trades_today": self._risk_state.trades_today,
            "last_entry_time": self._risk_state.last_entry_time,
        }

    def record_entry(self, entry_time: datetime) -> None:
        self._risk_state.trades_today += 1
        self._risk_state.last_entry_time = entry_time if entry_time.tzinfo else entry_time.replace(tzinfo=ET)

    def record_exit(self, pnl_usd: Decimal) -> None:
        self._risk_state.daily_pnl += pnl_usd
        if pnl_usd < 0:
            self._risk_state.consecutive_losses += 1
        else:
            self._risk_state.consecutive_losses = 0

    def set_kill_switch(self, active: bool) -> None:
        self._risk_state.kill_switch_active = active

    def reset_session(self) -> None:
        self._risk_state.last_entry_time = None
        self._risk_state.consecutive_losses = 0
        # Keep daily_pnl and trades_today until day boundary
