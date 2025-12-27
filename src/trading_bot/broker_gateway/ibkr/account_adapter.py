from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class AccountAdapter:
    _ib: Any = None  # ib_insync connection
    _cache: Dict[str, Any] = field(default_factory=dict)
    _cache_ts: Optional[float] = None
    cache_ttl_seconds: int = 5

    def set_connection(self, ib: Any) -> None:
        """Set the ib_insync IB instance for this adapter."""
        self._ib = ib

    def get_position_snapshot(self) -> Dict[str, Any]:
        """Return current MES position (placeholder if no ib_insync)."""
        if not self._ib:
            return {"symbol": "MES", "position": 0, "avg_price": 0.0, "unrealized_pnl": 0.0}
        
        try:
            positions = self._ib.positions()
            for pos in positions:
                if pos.contract.symbol == "MES":
                    return {
                        "symbol": "MES",
                        "position": int(pos.position),
                        "avg_price": float(pos.avgCost or 0.0),
                        "unrealized_pnl": float(pos.unrealizedPNL or 0.0),
                    }
        except Exception:
            pass
        
        return {"symbol": "MES", "position": 0, "avg_price": 0.0, "unrealized_pnl": 0.0}

    def get_account_snapshot(self) -> Dict[str, Any]:
        """Fetch account summary: equity, buying power, margin."""
        if not self._ib:
            return {
                "equity": 0.0,
                "buying_power": 0.0,
                "maintenance_margin": 0.0,
                "initial_margin": 0.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
            }
        
        try:
            summary_data = self._ib.accountSummary()
            summary = {item.tag: float(item.value) for item in summary_data if item.tag}
            
            return {
                "equity": summary.get("NetLiquidation", 0.0),
                "buying_power": summary.get("AvailableFunds", summary.get("BuyingPower", 0.0)),
                "maintenance_margin": summary.get("MaintenanceMargin", 0.0),
                "initial_margin": summary.get("InitialMargin", 0.0),
                "realized_pnl": summary.get("RealizedPnL", 0.0),
                "unrealized_pnl": summary.get("UnrealizedPnL", 0.0),
            }
        except Exception:
            return {
                "equity": 0.0,
                "buying_power": 0.0,
                "maintenance_margin": 0.0,
                "initial_margin": 0.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
            }
