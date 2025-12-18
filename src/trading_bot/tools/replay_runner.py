from __future__ import annotations

import argparse
import json
from typing import List, Optional, Dict, Any
from pathlib import Path
import yaml

from trading_bot.core.runner import BotRunner
from trading_bot.log.event_store import EventStore


def _load_runtime_config(default_path: str = "src/trading_bot/runtime.yaml") -> Dict[str, Any]:
    p = Path(default_path)
    if p.exists():
        with p.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def replay_stream(
    db_path: str,
    stream_id: str,
    contracts_path: str = "src/trading_bot/contracts",
    adapter: Optional[str] = None,
    fill_mode: Optional[str] = None,
    adapter_kwargs: Optional[Dict[str, Any]] = None,
) -> None:
    store = EventStore(db_path)
    events = store.read_stream(stream_id)
    rt = _load_runtime_config()
    ad_name = adapter or (rt.get("adapter") or "tradovate")
    fm = (fill_mode or rt.get("fill_mode") or "IMMEDIATE").upper()
    a_kwargs = adapter_kwargs or rt.get("adapter_kwargs") or {}
    runner = BotRunner(contracts_path=contracts_path, db_path=db_path, adapter=ad_name, fill_mode=fm, adapter_kwargs=a_kwargs)
    processed = 0
    for e in events:
        if e.type != "BAR_1M":
            continue
        bar = {"ts": e.ts, **e.payload}
        decision = runner.run_once(bar, stream_id=stream_id)
        processed += 1
    print(json.dumps({"stream_id": stream_id, "bars_processed": processed}, indent=2))


def replay_json(
    bars_path: str,
    db_path: str,
    stream_id: str = "MES_RTH",
    contracts_path: str = "src/trading_bot/contracts",
    adapter: Optional[str] = None,
    fill_mode: Optional[str] = None,
    adapter_kwargs: Optional[Dict[str, Any]] = None,
) -> None:
    with open(bars_path, "r", encoding="utf-8") as f:
        bars: List[dict] = json.load(f)
    rt = _load_runtime_config()
    ad_name = adapter or (rt.get("adapter") or "tradovate")
    fm = (fill_mode or rt.get("fill_mode") or "IMMEDIATE").upper()
    a_kwargs = adapter_kwargs or rt.get("adapter_kwargs") or {}
    runner = BotRunner(contracts_path=contracts_path, db_path=db_path, adapter=ad_name, fill_mode=fm, adapter_kwargs=a_kwargs)
    processed = 0
    for bar in bars:
        runner.run_once(bar, stream_id=stream_id)
        processed += 1
    print(json.dumps({"stream_id": stream_id, "bars_processed": processed}, indent=2))


def main():
    p = argparse.ArgumentParser("replay-runner")
    sub = p.add_subparsers(dest="cmd", required=True)

    s_stream = sub.add_parser("stream")
    s_stream.add_argument("--db", default="data/events.sqlite")
    s_stream.add_argument("--stream", required=True)
    s_stream.add_argument("--contracts", default="src/trading_bot/contracts")
    s_stream.add_argument("--adapter", default=None, choices=["tradovate", "ninjatrader"], help="Execution adapter")
    s_stream.add_argument("--fill-mode", default=None, choices=["IMMEDIATE", "DELAYED", "PARTIAL", "TIMEOUT"], help="SIM fill mode (Tradovate)")

    s_json = sub.add_parser("json")
    s_json.add_argument("--bars", required=True, help="Path to JSON list of bar dicts")
    s_json.add_argument("--db", default="data/events.sqlite")
    s_json.add_argument("--stream", default="MES_RTH")
    s_json.add_argument("--contracts", default="src/trading_bot/contracts")
    s_json.add_argument("--adapter", default=None, choices=["tradovate", "ninjatrader"], help="Execution adapter")
    s_json.add_argument("--fill-mode", default=None, choices=["IMMEDIATE", "DELAYED", "PARTIAL", "TIMEOUT"], help="SIM fill mode (Tradovate)")

    args = p.parse_args()
    if args.cmd == "stream":
        replay_stream(args.db, args.stream, contracts_path=args.contracts, adapter=args.adapter, fill_mode=getattr(args, "fill_mode", None))
    elif args.cmd == "json":
        replay_json(args.bars, args.db, stream_id=args.stream, contracts_path=args.contracts, adapter=args.adapter, fill_mode=getattr(args, "fill_mode", None))


if __name__ == "__main__":
    main()
