from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
from decimal import Decimal

from trading_bot.core.state_store import RiskState, ET


class PersistentStateStore:
    """
    Lightweight JSON persistence for risk/belief state between sessions.
    - Stores risk metrics (daily_pnl, trades_today, consecutive_losses, last_entry_time, kill_switch_active)
    - Stores belief state blob (caller-provided)
    Intended for SIM / local use; not optimized for concurrency.
    """

    def __init__(self, path: str = "data/state.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._risk_state = RiskState()
        self._belief_state: Dict[str, Any] = {}
        self._loaded = False

    def load(self) -> None:
        if not self.path.exists():
            self._loaded = True
            return
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        rs = data.get("risk_state", {}) if isinstance(data, dict) else {}
        self._risk_state = RiskState(
            kill_switch_active=bool(rs.get("kill_switch_active", False)),
            daily_pnl=Decimal(str(rs.get("daily_pnl", "0"))),
            consecutive_losses=int(rs.get("consecutive_losses", 0)),
            trades_today=int(rs.get("trades_today", 0)),
            last_entry_time=self._parse_dt(rs.get("last_entry_time")),
        )
        self._belief_state = data.get("belief_state", {}) if isinstance(data, dict) else {}
        self._loaded = True

    def save(self) -> None:
        payload = {
            "risk_state": {
                "kill_switch_active": self._risk_state.kill_switch_active,
                "daily_pnl": str(self._risk_state.daily_pnl),
                "consecutive_losses": self._risk_state.consecutive_losses,
                "trades_today": self._risk_state.trades_today,
                "last_entry_time": self._risk_state.last_entry_time.isoformat() if self._risk_state.last_entry_time else None,
            },
            "belief_state": self._belief_state,
        }
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    @staticmethod
    def _parse_dt(s: Optional[str]) -> Optional[datetime]:
        if not s:
            return None
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ET)
            return dt
        except Exception:
            return None

    # Accessors to integrate with BotRunner
    def get_risk_state(self) -> RiskState:
        if not self._loaded:
            self.load()
        return self._risk_state

    def set_risk_state(self, rs: RiskState) -> None:
        self._risk_state = rs

    def get_belief_state(self) -> Dict[str, Any]:
        if not self._loaded:
            self.load()
        return self._belief_state

    def set_belief_state(self, beliefs: Dict[str, Any]) -> None:
        self._belief_state = beliefs

