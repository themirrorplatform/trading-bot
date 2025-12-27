from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any

@dataclass
class SessionManager:
    flatten_deadline_et: str = "15:55"
    no_trade_windows: List[Dict[str, str]] = None

    def __post_init__(self):
        if self.no_trade_windows is None:
            self.no_trade_windows = [
                {"start": "09:30", "end": "09:35"},  # Open
                {"start": "11:30", "end": "13:30"},  # Lunch
                {"start": "15:55", "end": "16:00"},  # Close
            ]

    def is_past_flatten_deadline(self, now_et: datetime) -> bool:
        hhmm = now_et.strftime("%H:%M")
        return hhmm >= self.flatten_deadline_et

    def is_in_no_trade_window(self, now_et: datetime) -> bool:
        hhmm = now_et.strftime("%H:%M")
        for window in self.no_trade_windows:
            if window["start"] <= hhmm < window["end"]:
                return True
        return False
