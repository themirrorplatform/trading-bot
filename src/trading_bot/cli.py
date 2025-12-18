from __future__ import annotations
import argparse
import json
from trading_bot.log.event_store import EventStore
from trading_bot.core.runner import BotRunner
from trading_bot.tools.replay_runner import replay_stream, replay_json
from trading_bot.core.types import Event
from trading_bot.core.types import stable_json, sha256_hex
from trading_bot.core.config import load_yaml_contract
from decimal import Decimal
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def main():
    p = argparse.ArgumentParser("trading-bot")
    sub = p.add_subparsers(dest="cmd", required=True)

    # init-db
    s_init = sub.add_parser("init-db")
    s_init.add_argument("--db", default="data/events.sqlite")
    s_init.add_argument("--schema", default="src/trading_bot/log/schema.sql")

    # run-once from bar JSON
    s_run = sub.add_parser("run-once")
    s_run.add_argument("--bar-json", required=True, help="Path to JSON file with bar payload {ts,o,h,l,c,v}")
    s_run.add_argument("--db", default="data/events.sqlite")

    # replay from DB stream of BAR_1M
    s_replay_stream = sub.add_parser("replay-stream")
    s_replay_stream.add_argument("--db", default="data/events.sqlite")
    s_replay_stream.add_argument("--stream", required=True)
    s_replay_stream.add_argument("--contracts", default="src/trading_bot/contracts")

    # replay from JSON array of bars
    s_replay_json = sub.add_parser("replay-json")
    s_replay_json.add_argument("--bars", required=True)
    s_replay_json.add_argument("--db", default="data/events.sqlite")
    s_replay_json.add_argument("--stream", default="MES_RTH")
    s_replay_json.add_argument("--contracts", default="src/trading_bot/contracts")

    # seed demo BAR_1M events into DB
    s_seed = sub.add_parser("seed-demo-bars")
    s_seed.add_argument("--db", default="data/events.sqlite")
    s_seed.add_argument("--stream", default="MES_RTH_DEMO")
    s_seed.add_argument("--start-iso", default="2025-12-18T09:31:00-05:00")
    s_seed.add_argument("--count", type=int, default=30)

    args = p.parse_args()

    if args.cmd == "init-db":
        store = EventStore(args.db)
        store.init_schema(args.schema)
        print(f"Initialized DB at {args.db}")
        return

    if args.cmd == "run-once":
        with open(args.bar_json, "r", encoding="utf-8") as f:
            bar = json.load(f)
        runner = BotRunner(db_path=args.db)
        decision = runner.run_once(bar)
        print(json.dumps(decision, indent=2))
        return

    if args.cmd == "replay-stream":
        replay_stream(args.db, args.stream, contracts_path=args.contracts)
        return

    if args.cmd == "replay-json":
        replay_json(args.bars, args.db, stream_id=args.stream, contracts_path=args.contracts)
        return

    if args.cmd == "seed-demo-bars":
        ET = ZoneInfo("America/New_York")
        store = EventStore(args.db)
        # derive config hash similar to runner
        try:
            constitution = load_yaml_contract("src/trading_bot/contracts", "constitution.yaml")
            session = load_yaml_contract("src/trading_bot/contracts", "session.yaml")
            strategy_templates = load_yaml_contract("src/trading_bot/contracts", "strategy_templates.yaml")
            risk_model = load_yaml_contract("src/trading_bot/contracts", "risk_model.yaml")
        except Exception:
            constitution = {"missing": True}
            session = {"missing": True}
            strategy_templates = {"missing": True}
            risk_model = {"missing": True}
        cfg_sources = {
            "constitution": constitution,
            "session": session,
            "strategy_templates": strategy_templates,
            "risk_model": risk_model,
            "signal_params": {"tick_size": str(Decimal("0.25"))},
        }
        config_hash = sha256_hex(stable_json(cfg_sources))

        # build bars
        try:
            start_dt = datetime.fromisoformat(args.start_iso)
        except Exception:
            start_dt = datetime(2025, 12, 18, 9, 31, tzinfo=ET)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=ET)

        events = []
        cur = start_dt
        price = Decimal("5000.00")
        for i in range(args.count):
            # deterministic gentle move
            drift = Decimal(str(((i % 10) - 5)))  # -5..+4
            o = price + drift
            h = o + Decimal("3.00")
            l = o - Decimal("3.50")
            c = o + Decimal(str((i % 3) - 1))  # -1,0,1 pattern
            v = 1000 + (i * 50)
            payload = {"o": float(o), "h": float(h), "l": float(l), "c": float(c), "v": v}
            ts = cur.isoformat()
            e = Event.make(args.stream, ts, "BAR_1M", payload, config_hash)
            events.append(e)
            cur += timedelta(minutes=1)
        added = store.append_many(events)
        print(f"Seeded {added} BAR_1M events into stream {args.stream} at {args.db}")
        return


if __name__ == "__main__":
    main()
