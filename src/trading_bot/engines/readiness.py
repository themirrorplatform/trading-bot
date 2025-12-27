"""
Unified readiness snapshot computation for CLI and runner.
Computes PDH/PDL/PDC, ONH/ONL, VWAP proxy, ATR, volatility, trend, regime, and distances.
Handles ET timezone parsing, volume tracking, and DTE computation.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo


def compute_readiness_snapshot(
    bars: List[Dict[str, Any]],
    now_utc: Optional[datetime] = None,
    contract: Optional[Any] = None,
    data_quality: Optional[str] = None,
    last_tick_ts: Optional[str] = None,
    last_hist_bar_ts: Optional[str] = None,
    atr_window: int = 60,
) -> Dict[str, Any]:
    """
    Compute a complete readiness snapshot from historical bars.
    
    Args:
        bars: List of bar dicts {date, open, high, low, close, volume}.
        now_utc: Current UTC time (defaults to now).
        contract: IBKR contract object (for conId, lastTradeDateOrContractMonth).
        data_quality: Data quality flag ("LIVE", "DELAYED", "HISTORICAL_ONLY", etc.).
        last_tick_ts: ISO timestamp of last market data tick.
        last_hist_bar_ts: ISO timestamp of last historical bar.
        atr_window: Window size for ATR and volatility proxies (default 60).
    
    Returns:
        Dict with: last_close, atr_proxy, realized_vol_proxy, trend_slope_proxy, regime,
                   bar_count, levels (PDH, PDL, PDC, ONH, ONL, VWAP_PROXY), distances,
                   vwap_method, dte, now_utc, now_et, bars_converted_to,
                   levels_available, contract details.
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    
    ET = ZoneInfo("America/New_York")
    now_et = now_utc.astimezone(ET)
    
    # Extract and validate series
    closes = [float(b.get("close", 0.0)) for b in bars]
    highs = [float(b.get("high", 0.0)) for b in bars]
    lows = [float(b.get("low", 0.0)) for b in bars]
    vols = [float(b.get("volume", 0) or 0) for b in bars]
    
    last_close = float(closes[-1]) if closes else 0.0
    
    # Parse timestamps to ET
    dts: List[Optional[datetime]] = []
    for b in bars:
        raw = b.get("date")
        dt = None
        try:
            # ISO first
            dt = datetime.fromisoformat(raw)
        except Exception:
            try:
                # IBKR format: "yyyymmdd  HH:MM:SS"
                dt = datetime.strptime(str(raw), "%Y%m%d  %H:%M:%S")
            except Exception:
                dt = None
        if dt is not None and dt.tzinfo is None:
            # Assume ET if no tz
            dt = dt.replace(tzinfo=ET)
        if dt is not None:
            dts.append(dt.astimezone(ET))
        else:
            dts.append(None)
    
    # ATR proxy
    hl = [(highs[i] - lows[i]) for i in range(max(0, len(highs)-atr_window), len(highs))]
    atr_proxy = sum(hl) / len(hl) if hl else 0.0
    
    # Realized volatility proxy
    rets = []
    if len(closes) >= 2:
        for i in range(max(1, len(closes)-atr_window), len(closes)):
            try:
                base = closes[i-1]
                if base:
                    r = (closes[i] - base) / base
                    rets.append(r)
            except Exception:
                pass
    rv_proxy = 0.0
    if rets:
        m = sum(rets) / len(rets)
        var = sum((x - m) ** 2 for x in rets) / len(rets)
        rv_proxy = (var ** 0.5)
    
    # Trend slope proxy
    slope = 0.0
    if len(closes) >= 20:
        xs = list(range(len(closes)-20, len(closes)))
        ys = closes[-20:]
        n = len(xs)
        sx = sum(xs)
        sy = sum(ys)
        sxx = sum(x*x for x in xs)
        sxy = sum(x*y for x, y in zip(xs, ys))
        denom = (n*sxx - sx*sx)
        if denom != 0:
            slope = (n*sxy - sx*sy) / denom
    regime = "TREND" if abs(slope) > 0.5 else "CHOP"
    
    # Session-aware levels: PDH/PDL/PDC and ONH/ONL
    pdh = pdl = pdc = None
    onh = onl = None
    levels_available = False
    try:
        if dts and dts[-1] is not None:
            last_et = dts[-1]
            # RTH mask: 09:30-16:00 ET
            def is_rth(dt):
                if dt is None:
                    return False
                h = dt.hour + dt.minute / 60.0
                return 9.5 <= h <= 16.0
            
            # Group by ET date
            from collections import defaultdict
            by_date = defaultdict(list)
            for i, dt in enumerate(dts):
                if dt is None:
                    continue
                by_date[dt.date()].append(i)
            
            # Determine previous RTH date
            dates = sorted(by_date.keys())
            cur_date = last_et.date()
            prev_rth_date = None
            for d in reversed(dates):
                if d >= cur_date:
                    continue
                idxs = [i for i in by_date[d] if is_rth(dts[i])]
                if idxs:
                    prev_rth_date = d
                    break
            
            if prev_rth_date is not None:
                idxs = [i for i in by_date[prev_rth_date] if is_rth(dts[i])]
                vals_h = [highs[i] for i in idxs]
                vals_l = [lows[i] for i in idxs]
                vals_c = [closes[i] for i in idxs]
                if vals_h:
                    pdh = max(vals_h)
                if vals_l:
                    pdl = min(vals_l)
                if vals_c:
                    pdc = vals_c[-1]
                if pdh is not None or pdl is not None or pdc is not None:
                    levels_available = True
            
            # Overnight: prev day 18:00 to current day 09:30 ET
            overnight_start = datetime.combine(last_et.date(), time(18, 0, tzinfo=ET))
            overnight_end = datetime.combine(last_et.date(), time(9, 30, tzinfo=ET))
            # If last bar is before 09:30, overnight is from previous calendar date 18:00
            if last_et.hour < 9 or (last_et.hour == 9 and last_et.minute < 30):
                overnight_start = overnight_start - timedelta(days=1)
            on_idxs = [i for i, dt in enumerate(dts) if dt is not None and overnight_start <= dt <= overnight_end]
            if on_idxs:
                onh = max(highs[i] for i in on_idxs)
                onl = min(lows[i] for i in on_idxs)
                levels_available = True
    except Exception:
        pass
    
    # VWAP proxy: typical price volume-weighted over last N bars
    vwap_proxy = None
    vwap_method = None
    try:
        tp = [(highs[i] + lows[i] + closes[i]) / 3.0 for i in range(len(closes))]
        i0 = max(0, len(closes) - atr_window)
        vols_window = vols[i0:]
        tp_window = tp[i0:]
        
        # Check if we have meaningful volume data
        has_volume = sum(1 for v in vols_window if v > 0)
        total_vol = sum(vols_window)
        
        if total_vol > 0 and has_volume / len(vols_window) >= 0.5:
            # Compute volume-weighted VWAP
            num = sum(tp_window[i] * vols_window[i] for i in range(len(tp_window)))
            vwap_proxy = num / total_vol
            vwap_method = "VOLUME_WEIGHTED"
        else:
            # Fallback to simple mean
            vwap_proxy = sum(tp_window) / len(tp_window) if tp_window else 0.0
            vwap_method = "SIMPLE_MEAN"
    except Exception:
        vwap_proxy = None
        vwap_method = None
    
    # Distances from last_close in points and ATR multiples
    def _dist(level):
        if level is None:
            return None
        pts = float(level) - float(last_close)
        atr_mul = (pts / atr_proxy) if atr_proxy else None
        return {"points": round(pts, 2), "atr": round(atr_mul, 2) if atr_mul else None}
    
    levels = {
        "PDH": pdh,
        "PDL": pdl,
        "PDC": pdc,
        "ONH": onh,
        "ONL": onl,
        "VWAP_PROXY": vwap_proxy,
    }
    distances = {k: _dist(v) for k, v in levels.items()}
    
    # DTE (days to expiry)
    dte = None
    contract_month = None
    contract_id = None
    if contract:
        try:
            contract_id = getattr(contract, "conId", None)
            raw_expiry = getattr(contract, "lastTradeDateOrContractMonth", None)
            contract_month = raw_expiry
            if raw_expiry:
                try:
                    if len(str(raw_expiry)) == 8:
                        # YYYYMMDD format
                        expiry_dt = datetime.strptime(str(raw_expiry), "%Y%m%d").date()
                    else:
                        # YYYYMM format: assume 20th
                        ym = str(raw_expiry)
                        if len(ym) == 6:
                            expiry_dt = date(int(ym[0:4]), int(ym[4:6]), 20)
                        else:
                            expiry_dt = None
                    if expiry_dt:
                        dte = (expiry_dt - now_et.date()).days
                except Exception:
                    dte = None
        except Exception:
            pass
    
    # Build final payload
    payload = {
        "timestamp": now_utc.isoformat(),
        "now_utc": now_utc.isoformat(),
        "now_et": now_et.isoformat(),
        "bars_converted_to": "America/New_York",
        "bars_timezone_detected": "US/Central or US/Eastern from IBKR",
        "last_close": round(last_close, 2),
        "atr_proxy": round(atr_proxy, 2),
        "realized_vol_proxy": round(rv_proxy, 4),
        "trend_slope_proxy": round(slope, 4),
        "regime": regime,
        "bar_count": len(bars),
        "levels": {k: round(v, 2) if isinstance(v, float) else v for k, v in levels.items()},
        "distances": distances,
        "vwap_method": vwap_method,
        "dte": dte,
        "contract_id": contract_id,
        "contract_month": contract_month,
        "levels_available": levels_available,
        "data_quality": data_quality,
        "last_tick_ts": last_tick_ts,
        "last_hist_bar_ts": last_hist_bar_ts,
    }
    
    return payload
