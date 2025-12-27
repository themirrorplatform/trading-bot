from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Tuple
from datetime import datetime

ALLOW = ("ALLOW", "passed_all_checks")

@dataclass
class ConstitutionalState:
    daily_loss: float
    consecutive_losses: int
    trades_today: int
    current_position: int
    current_time_et: str  # HH:MM
    current_dvs: float
    current_eqs: float

@dataclass
class Constitution:
    max_daily_loss: float = 30.0
    max_consecutive_losses: int = 2
    max_trades_per_day: int = 2
    max_position: int = 1
    dvs_min_for_entry: float = 0.80
    eqs_min_for_entry: float = 0.75
    flatten_deadline: str = "15:55"


def filter_order_intent(intent: Dict[str, Any], state: ConstitutionalState, const: Constitution = Constitution()) -> Tuple[str, str]:
    # Daily loss gate
    if state.daily_loss >= const.max_daily_loss:
        return ("REJECT", "daily_loss_exceeded")
    # Consecutive losses gate
    if state.consecutive_losses >= const.max_consecutive_losses:
        return ("REJECT", "consecutive_loss_pause")
    # Trades per day gate
    if state.trades_today >= const.max_trades_per_day:
        return ("REJECT", "max_trades_reached")
    # Position limit gate
    qty = int(intent.get("contracts") or intent.get("quantity") or 1)
    if (state.current_position + qty) > const.max_position:
        return ("REJECT", "max_position_exceeded")
    # Flatten deadline gate
    if (state.current_time_et or "") >= const.flatten_deadline:
        return ("REJECT", "past_flatten_deadline")
    # No-trade windows check (integrate SessionManager)
    from trading_bot.broker_gateway.ibkr.session_manager import SessionManager
    sm = SessionManager()
    try:
        # Parse HH:MM to datetime for checking
        hour, minute = map(int, state.current_time_et.split(":"))
        mock_dt = datetime(2025, 1, 1, hour, minute)
        if sm.is_in_no_trade_window(mock_dt):
            return ("REJECT", "no_trade_window")
    except Exception:
        pass
    # DVS gate
    if float(state.current_dvs) < const.dvs_min_for_entry:
        return ("REJECT", "dvs_too_low")
    # EQS gate
    if float(state.current_eqs) < const.eqs_min_for_entry:
        return ("REJECT", "eqs_too_low")
    return ALLOW
