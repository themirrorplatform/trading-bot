"""
Market Data Manager for IBKR: Real-time bar subscription, quality gating, reconnect.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Optional, List
from decimal import Decimal


@dataclass
class DataQualityMetrics:
    timestamp_gap_seconds: int = 0
    is_rth: bool = True
    spread_ticks: Optional[float] = None
    volume: int = 0
    true_range: Decimal = Decimal("0")
    bar_age_seconds: int = 0
    

@dataclass
class MarketDataManager:
    _ib: Any = None
    _contract: Any = None
    _last_bar: Optional[Dict[str, Any]] = None
    _last_bar_time: Optional[datetime] = None
    _on_bar: Optional[Callable[[Dict[str, Any]], None]] = None
    _heartbeat_interval_seconds: int = 30
    _last_heartbeat: Optional[datetime] = None
    _stale_threshold_seconds: int = 60
    _quality_score: float = 1.0
    _bar_buffer: List[Dict[str, Any]] = field(default_factory=list)
    _max_buffer_bars: int = 100
    _reference_atr: Optional[Decimal] = None
    _rth_start: str = "09:30"
    _rth_end: str = "16:00"

    def set_connection(self, ib: Any, mes_contract: Any) -> None:
        """Set ib_insync connection and contract."""
        self._ib = ib
        self._contract = mes_contract

    def subscribe(self, on_bar: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        """Subscribe to real-time bars from IBKR."""
        self._on_bar = on_bar
        if not self._ib:
            return
        
        try:
            import ib_insync as ibis
            # Request real-time bars (5 seconds granularity; we'll aggregate to 1-min)
            self._ib.reqRealTimeBars(
                self._contract, 5, "TRADES", useRTH=True
            )
            # Attach callback
            self._ib.barUpdateEvent += self._on_bar_update
            self._last_heartbeat = datetime.utcnow()
        except Exception as e:
            self._quality_score = 0.5
            pass

    def _on_bar_update(self, bars, hasNewBar: bool) -> None:
        """Callback when real-time bar updates."""
        if not hasNewBar or not bars:
            return
        
        try:
            bar = bars[-1]
            now = datetime.utcnow()
            
            # Parse bar into our format
            bar_dict = {
                "ts": bar.time.isoformat() if hasattr(bar.time, "isoformat") else str(bar.time),
                "o": float(bar.open),
                "h": float(bar.high),
                "l": float(bar.low),
                "c": float(bar.close),
                "v": int(bar.volume),
                "bid": float(getattr(bar, "bid", bar.close - 0.5)),
                "ask": float(getattr(bar, "ask", bar.close + 0.5)),
            }
            
            # Compute quality metrics
            metrics = self._compute_quality_metrics(bar_dict, now)
            bar_dict["quality_metrics"] = metrics
            bar_dict["data_quality_score"] = self._quality_score
            
            # Buffer and aggregate (1-min bars from 5-sec RealTimeBars)
            self._bar_buffer.append(bar_dict)
            if len(self._bar_buffer) > self._max_buffer_bars:
                self._bar_buffer.pop(0)
            
            # If we have enough buffered bars (12 x 5-sec = 1-min), emit aggregated bar
            if len(self._bar_buffer) >= 12:
                agg_bar = self._aggregate_bars(self._bar_buffer[-12:])
                self._last_bar = agg_bar
                self._last_bar_time = now
                
                if self._on_bar:
                    self._on_bar(agg_bar)
        except Exception as e:
            self._quality_score = max(0.0, self._quality_score - 0.1)
            pass

    def _compute_quality_metrics(self, bar: Dict[str, Any], now: datetime) -> DataQualityMetrics:
        """Compute data quality metrics for this bar."""
        # Timestamp gap check
        gap_seconds = 0
        if self._last_bar_time:
            gap_seconds = int((now - self._last_bar_time).total_seconds())
        
        # RTH check (roughly 09:30 - 16:00 ET)
        is_rth = self._check_rth(now)
        
        # Spread as ticks
        tick_size = 0.25
        spread_ticks = (bar["ask"] - bar["bid"]) / tick_size if bar["ask"] > 0 and bar["bid"] > 0 else 1.0
        
        # Volume
        volume = bar["v"]
        
        # True range
        high = Decimal(str(bar["h"]))
        low = Decimal(str(bar["l"]))
        close = Decimal(str(bar["c"]))
        tr = max(high - low, abs(high - (self._last_bar["c"] if self._last_bar else close)), abs(low - (self._last_bar["c"] if self._last_bar else close)))
        
        # Bar age (latency)
        bar_age = gap_seconds
        
        return DataQualityMetrics(
            timestamp_gap_seconds=gap_seconds,
            is_rth=is_rth,
            spread_ticks=spread_ticks,
            volume=volume,
            true_range=tr,
            bar_age_seconds=bar_age,
        )

    def _check_rth(self, ts: datetime) -> bool:
        """Check if time is within RTH."""
        hm = ts.strftime("%H:%M")
        return self._rth_start <= hm < self._rth_end

    def _aggregate_bars(self, bars: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate multiple 5-sec bars into 1-min bar."""
        if not bars:
            return {}
        
        o = bars[0]["o"]
        h = max(b["h"] for b in bars)
        l = min(b["l"] for b in bars)
        c = bars[-1]["c"]
        v = sum(b["v"] for b in bars)
        bid = bars[-1]["bid"]
        ask = bars[-1]["ask"]
        ts = bars[-1]["ts"]
        
        # Use worst quality score from component bars
        quality_score = min(b.get("data_quality_score", 1.0) for b in bars)
        
        return {
            "ts": ts,
            "o": o,
            "h": h,
            "l": l,
            "c": c,
            "v": v,
            "bid": bid,
            "ask": ask,
            "data_quality_score": quality_score,
        }

    def get_quality_score(self) -> float:
        """Return current data quality score."""
        return self._quality_score

    def heartbeat(self) -> None:
        """Update heartbeat; degrade quality if stale."""
        now = datetime.utcnow()
        if self._last_bar_time:
            age = (now - self._last_bar_time).total_seconds()
            if age > self._stale_threshold_seconds:
                self._quality_score = max(0.0, self._quality_score - 0.2)
        self._last_heartbeat = now

    def unsubscribe(self) -> None:
        """Unsubscribe from data."""
        if self._ib:
            try:
                self._ib.barUpdateEvent -= self._on_bar_update
            except Exception:
                pass

    def get_last_bar(self) -> Optional[Dict[str, Any]]:
        """Return last aggregated bar."""
        return self._last_bar
