from __future__ import annotations

from typing import Any

from trading_bot.adapters.tradovate import TradovateSimAdapter, TradovateLiveAdapter


def create_adapter(name: str = "tradovate", **kwargs: Any):
    n = (name or "").strip().lower()
    mode = (kwargs.get("mode") or "SIMULATED").upper()

    if n in ("tradovate", "tv", "sim", "tradovate-sim", "tradovate-live", "tv-live"):
        if mode == "LIVE" or n in ("tradovate-live", "tv-live"):
            return TradovateLiveAdapter(
                api_url=kwargs.get("api_url") or "https://live.tradovateapi.com/v1",
                ws_url=kwargs.get("ws_url"),
                account_id=kwargs.get("account_id"),
                access_token=kwargs.get("access_token"),
                instrument=kwargs.get("instrument") or "MES",
                heartbeat_interval=int(kwargs.get("heartbeat_interval", 10)),
                reconnect_interval=int(kwargs.get("reconnect_interval", 20)),
                poll_interval=int(kwargs.get("poll_interval", 5)),
            )
        # Pass through optional fill_mode for SIM
        fill_mode = (kwargs.get("fill_mode") or "IMMEDIATE").upper()
        return TradovateSimAdapter(mode="SIMULATED", fill_mode=fill_mode)
    elif n in ("ninjatrader", "nt", "bridge"):
        from trading_bot.adapters.ninjatrader_bridge import NinjaTraderBridgeAdapter
        base_url = kwargs.get("base_url") or "http://127.0.0.1:8123"
        auth_token = kwargs.get("auth_token") or "changeme"
        return NinjaTraderBridgeAdapter(base_url=base_url, auth_token=auth_token)
    else:
        raise ValueError(f"Unknown adapter name: {name}")
