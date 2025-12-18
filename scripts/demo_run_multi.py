import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Ensure package path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from trading_bot.core.runner import BotRunner

ET = ZoneInfo("America/New_York")


def make_bar(ts, o, h, l, c, v):
    return {"symbol": "MES", "ts": ts.isoformat(), "o": o, "h": h, "l": l, "c": c, "v": v}


def build_bars():
    # Start during mid-morning session to satisfy session gate
    start = datetime(2025, 1, 2, 10, 30, tzinfo=ET)
    bars = []

    # Warmup bars (15) to build ATR/VWAP around ~100.0 with modest ranges
    price = 100.0
    for i in range(15):
        ts = start + timedelta(minutes=i)
        drift = 0.02 * i
        o = price + drift
        c = o + 0.05  # slight uptick
        h = c + 0.10
        l = o - 0.10
        bars.append(make_bar(ts, o, h, l, c, 1500))

    # Signal bar: drop below VWAP by ~0.4% while keeping range reasonable
    ts = start + timedelta(minutes=15)
    o = 100.3
    h = 100.4
    l = 99.6
    c = 99.7  # below expected VWAP
    bars.append(make_bar(ts, o, h, l, c, 1800))

    return bars


def main():
    bars = build_bars()
    runner = BotRunner()
    for b in bars:
        decision = runner.run_once(b)
        print(decision)


if __name__ == "__main__":
    main()
