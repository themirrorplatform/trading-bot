from __future__ import annotations

from typing import Any

from trading_bot.adapters.tradovate import TradovateAdapter


def create_adapter(name: str = "tradovate", **kwargs: Any):
    n = (name or "").strip().lower()
    if n in ("tradovate", "tv", "sim"):
        # Pass through optional fill_mode
        fill_mode = (kwargs.get("fill_mode") or "IMMEDIATE").upper()
        return TradovateAdapter(mode="SIMULATED", fill_mode=fill_mode)
    elif n in ("ninjatrader", "nt", "bridge"):
        from trading_bot.adapters.ninjatrader_bridge import NinjaTraderBridgeAdapter
        base_url = kwargs.get("base_url") or "http://127.0.0.1:8123"
        auth_token = kwargs.get("auth_token") or "changeme"
        return NinjaTraderBridgeAdapter(base_url=base_url, auth_token=auth_token)
    else:
        raise ValueError(f"Unknown adapter name: {name}")
