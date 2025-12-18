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
    s_run.add_argument("--adapter", default="tradovate", choices=["tradovate", "ninjatrader"], help="Execution adapter")
    s_run.add_argument("--fill-mode", default="IMMEDIATE", choices=["IMMEDIATE", "DELAYED", "PARTIAL", "TIMEOUT"], help="SIM fill mode (Tradovate)")

    # replay from DB stream of BAR_1M
    s_replay_stream = sub.add_parser("replay-stream")
    s_replay_stream.add_argument("--db", default="data/events.sqlite")
    s_replay_stream.add_argument("--stream", required=True)
    s_replay_stream.add_argument("--contracts", default="src/trading_bot/contracts")
    s_replay_stream.add_argument("--adapter", default="tradovate", choices=["tradovate", "ninjatrader"])
    s_replay_stream.add_argument("--fill-mode", default="IMMEDIATE", choices=["IMMEDIATE", "DELAYED", "PARTIAL", "TIMEOUT"])

    # replay from JSON array of bars
    s_replay_json = sub.add_parser("replay-json")
    s_replay_json.add_argument("--bars", required=True)
    s_replay_json.add_argument("--db", default="data/events.sqlite")
    s_replay_json.add_argument("--stream", default="MES_RTH")
    s_replay_json.add_argument("--contracts", default="src/trading_bot/contracts")
    s_replay_json.add_argument("--adapter", default="tradovate", choices=["tradovate", "ninjatrader"])
    s_replay_json.add_argument("--fill-mode", default="IMMEDIATE", choices=["IMMEDIATE", "DELAYED", "PARTIAL", "TIMEOUT"])

    # seed demo BAR_1M events into DB
    s_seed = sub.add_parser("seed-demo-bars")
    s_seed.add_argument("--db", default="data/events.sqlite")
    s_seed.add_argument("--stream", default="MES_RTH_DEMO")
    s_seed.add_argument("--start-iso", default="2025-12-18T09:31:00-05:00")
    s_seed.add_argument("--count", type=int, default=30)

    # simple report dashboard
    s_report = sub.add_parser("report")
    s_report.add_argument("--db", default="data/events.sqlite")
    s_report.add_argument("--stream", required=True)

    args = p.parse_args()

    if args.cmd == "init-db":
        store = EventStore(args.db)
        store.init_schema(args.schema)
        print(f"Initialized DB at {args.db}")
        return

    if args.cmd == "run-once":
        with open(args.bar_json, "r", encoding="utf-8") as f:
            bar = json.load(f)
        runner = BotRunner(db_path=args.db, adapter=args.adapter, fill_mode=args.fill_mode)
        decision = runner.run_once(bar)
        print(json.dumps(decision, indent=2))
        return

    if args.cmd == "replay-stream":
        # pass-through adapter is not yet supported by replay helpers; run via CLI run-once/replay-json for adapter control
        replay_stream(args.db, args.stream, contracts_path=args.contracts)
        return

    if args.cmd == "replay-json":
        # replay_json builds its own runner internally today; for adapter control use run-once path or extend replay helpers
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

    if args.cmd == "report":
        store = EventStore(args.db)
        events = store.read_stream(args.stream)
        recon = 0
        desync = 0
        cancels = 0
        skip_hist = {}
        kill_hist = {}
        for e in events:
            if e.type == "RECONCILIATION":
                recon += 1
                if e.payload.get("kill_switch"):
                    desync += 1
                    reason = e.payload.get("kill_reason", "UNKNOWN")
                    kill_hist[reason] = kill_hist.get(reason, 0) + 1
                for a in e.payload.get("actions", []) or []:
                    if a.get("action") == "CANCEL":
                        cancels += 1
            if e.type == "DECISION_RECORD":
                rc = (e.payload.get("reasons") or {}).get("reason_code")
                if rc:
                    skip_hist[rc] = skip_hist.get(rc, 0) + 1
        print("Reconciliation summary:")
        print(f"  events: {recon}")
        print(f"  desync_kills: {desync}")
        print(f"  ttl_cancels: {cancels}")
        print("Skip reasons (top 10):")
        for k, v in sorted(skip_hist.items(), key=lambda kv: kv[1], reverse=True)[:10]:
            print(f"  {k}: {v}")
        print("Kill causes:")
        for k, v in sorted(kill_hist.items(), key=lambda kv: kv[1], reverse=True):
            print(f"  {k}: {v}")
        return


if __name__ == "__main__":
    main()
