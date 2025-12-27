from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

try:
    from ..adapters.ibkr_adapter import IBKRAdapter
except Exception:
    try:
        from trading_bot.adapters.ibkr_adapter import IBKRAdapter
    except Exception:
        # Fallback for direct script execution without package context
        import os, sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from adapters.ibkr_adapter import IBKRAdapter


def main() -> None:
    ap = argparse.ArgumentParser(description="IBKR historical backfill helper")
    ap.add_argument("--symbol", default="MES", help="Symbol, e.g., MES")
    ap.add_argument("--exchange", default="CME", help="Exchange, e.g., CME")
    ap.add_argument("--duration", default="3 D", help="DurationStr, e.g., '3 D', '1 W'")
    ap.add_argument("--bar", default="5 mins", help="Bar size, e.g., '1 min', '5 mins'")
    ap.add_argument("--show", default="TRADES", help="whatToShow: TRADES, MIDPOINT, BID, ASK")
    ap.add_argument("--useRTH", default="false", help="Restrict to Regular Trading Hours (true/false)")
    ap.add_argument("--mdType", default="4", help="Market data type: 1 real, 2 frozen, 3 delayedFrozen, 4 delayed")
    ap.add_argument("--outfile", default="", help="Optional output JSON file path")
    args = ap.parse_args()

    use_rth = str(args.useRTH).lower().strip() in ("1", "true", "yes")
    md_type = int(args.mdType)

    adapter = IBKRAdapter(mode="LIVE")
    bars: List[Dict[str, Any]] = adapter.req_historical_bars(
        symbol=args.symbol,
        exchange=args.exchange,
        durationStr=args.duration,
        barSizeSetting=args.bar,
        whatToShow=args.show,
        useRTH=use_rth,
        marketDataType=md_type,
    )

    print({
        "Symbol": args.symbol,
        "Exchange": args.exchange,
        "Count": len(bars),
        "BarSize": args.bar,
        "Duration": args.duration,
        "useRTH": use_rth,
        "marketDataType": md_type,
    })

    if bars:
        print("First bar:", bars[0])
        print("Last bar:", bars[-1])

    if args.outfile:
        # Convert datetime to ISO strings for JSON serialization
        serializable: List[Dict[str, Any]] = []
        for b in bars:
            row = dict(b)
            d = row.get("date")
            if hasattr(d, "isoformat"):
                row["date"] = d.isoformat()
            serializable.append(row)
        with open(args.outfile, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2)
        print({"Saved": args.outfile, "Rows": len(serializable)})


if __name__ == "__main__":
    main()
