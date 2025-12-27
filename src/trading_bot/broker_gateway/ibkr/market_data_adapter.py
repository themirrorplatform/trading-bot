from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Any
from datetime import datetime

@dataclass
class MarketDataAdapter:
    on_bar_closed: Callable[[Dict[str, Any]], None] | None = None
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 2
    _ib: Any | None = None
    _mes_contract: Any | None = None

    def _ensure_connection(self) -> bool:
        if self._ib:
            return True
        try:
            import ib_insync as ibis
            self._ib = ibis.IB()
            self._ib.connect(self.host, self.port, clientId=self.client_id)
            self._mes_contract = ibis.Future(symbol="MES", exchange="CME", currency="USD")
            self._ib.qualifyContracts(self._mes_contract)
            return True
        except Exception:
            return False

    def subscribe_mes_bars(self) -> None:
        """Subscribe to real-time 1-minute bars for MES."""
        if not self._ensure_connection():
            return
        try:
            import ib_insync as ibis
            bars = self._ib.reqRealTimeBars(
                self._mes_contract, 5, "TRADES", False
            )
            bars.updateEvent += self._on_bar_update
        except Exception:
            pass

    def _on_bar_update(self, bars, hasNewBar: bool) -> None:
        if not hasNewBar or not bars:
            return
        bar = bars[-1]
        # Emit MARKET_BAR_CLOSED event
        bar_dict = {
            "ts": bar.time.isoformat() if hasattr(bar.time, "isoformat") else str(bar.time),
            "o": float(bar.open),
            "h": float(bar.high),
            "l": float(bar.low),
            "c": float(bar.close),
            "v": int(bar.volume),
            "dvs": 1.0,  # Placeholder; compute DVS penalties
            "dvs_penalties": [],
        }
        self.emit_bar(bar_dict)

    def emit_bar(self, bar: Dict[str, Any]) -> None:
        if self.on_bar_closed:
            self.on_bar_closed(bar)
