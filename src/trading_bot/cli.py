from __future__ import annotations
import argparse
import json
import os
import sys
import logging
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

    # ==================== LIVE TRADING ====================

    # live - Start live trading
    s_live = sub.add_parser("live", help="Start live trading")
    s_live.add_argument("--symbol", default="MESZ4", help="Symbol to trade")
    s_live.add_argument("--environment", choices=["demo", "live"], default="demo",
                        help="Tradovate environment")
    s_live.add_argument("--db", default="data/events.sqlite")
    s_live.add_argument("--contracts", default="src/trading_bot/contracts")
    s_live.add_argument("--stream", default="MES_LIVE")
    s_live.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    # status - Get runner status
    s_status = sub.add_parser("status", help="Get trading bot status")
    s_status.add_argument("--db", default="data/events.sqlite")

    # kill - Activate kill switch
    s_kill = sub.add_parser("kill", help="Activate kill switch (flatten and stop)")
    s_kill.add_argument("--reason", default="MANUAL_KILL", help="Kill switch reason")

    # sync - Force sync to Supabase
    s_sync = sub.add_parser("sync", help="Force sync events to Supabase")
    s_sync.add_argument("--db", default="data/events.sqlite")

    # verify-config - Verify Tradovate and Supabase credentials
    s_verify = sub.add_parser("verify-config", help="Verify API credentials")

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

    # ==================== LIVE TRADING COMMANDS ====================

    if args.cmd == "live":
        # Set up logging
        log_level = logging.DEBUG if args.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("data/trading.log"),
            ],
        )

        # Check required environment variables
        required_vars = ["TRADOVATE_USERNAME", "TRADOVATE_PASSWORD"]
        missing = [v for v in required_vars if not os.environ.get(v)]
        if missing:
            print(f"Error: Missing environment variables: {', '.join(missing)}")
            print("\nSet these before running live trading:")
            print("  export TRADOVATE_USERNAME='your_username'")
            print("  export TRADOVATE_PASSWORD='your_password'")
            sys.exit(1)

        # Import and run
        from trading_bot.core.live_runner import LiveRunner, TradovateConfig, TradovateEnvironment

        config = TradovateConfig(
            username=os.environ["TRADOVATE_USERNAME"],
            password=os.environ["TRADOVATE_PASSWORD"],
            environment=TradovateEnvironment(args.environment),
        )

        def alert_callback(level: str, message: str):
            print(f"\n[ALERT:{level.upper()}] {message}")

        runner = LiveRunner(
            tradovate_config=config,
            symbol=args.symbol,
            stream_id=args.stream,
            contracts_path=args.contracts,
            db_path=args.db,
            on_alert=alert_callback,
        )

        print(f"Starting live trading: {args.symbol} on {args.environment}")
        print("Press Ctrl+C to stop\n")

        if runner.start():
            runner.run()
        else:
            print("Failed to start live runner")
            sys.exit(1)
        return

    if args.cmd == "status":
        # Show recent trading activity
        store = EventStore(args.db)
        print("Trading Bot Status")
        print("-" * 40)

        # Get recent events
        recent = store.query(limit=10)
        if recent:
            print(f"\nLast {len(recent)} events:")
            for event in recent:
                print(f"  {event['timestamp']} | {event['event_type']}")
        else:
            print("\nNo events found")

        # Check for Supabase connection
        url = os.environ.get("SUPABASE_URL")
        if url:
            print(f"\nSupabase: {url[:40]}...")
        else:
            print("\nSupabase: Not configured")

        return

    if args.cmd == "kill":
        print(f"Kill switch activated: {args.reason}")
        print("Note: This command only logs the kill. For live trading,")
        print("the kill switch in the runner will flatten and stop.")

        store = EventStore(args.db)
        ts = datetime.now(ZoneInfo("America/New_York")).isoformat()
        event = Event.make("SYSTEM", ts, "KILL_SWITCH", {
            "reason": args.reason,
            "source": "CLI",
        }, "manual")
        store.append(event)
        print(f"Kill event logged at {ts}")
        return

    if args.cmd == "sync":
        print("Force syncing events to Supabase...")
        from trading_bot.log.event_publisher import EventPublisher

        publisher = EventPublisher(sqlite_path=args.db)
        if publisher.start():
            synced = publisher.force_sync()
            print(f"Synced {synced} events")
            publisher.stop()
        else:
            print("Failed to start publisher (check SUPABASE_URL and SUPABASE_KEY)")
        return

    if args.cmd == "verify-config":
        print("Verifying configuration...")
        print("-" * 40)

        # Check Tradovate
        tv_user = os.environ.get("TRADOVATE_USERNAME")
        tv_pass = os.environ.get("TRADOVATE_PASSWORD")
        if tv_user and tv_pass:
            print(f"✓ Tradovate credentials set (user: {tv_user})")
        else:
            print("✗ Tradovate credentials missing")
            print("  Set TRADOVATE_USERNAME and TRADOVATE_PASSWORD")

        # Check Supabase
        sb_url = os.environ.get("SUPABASE_URL")
        sb_key = os.environ.get("SUPABASE_KEY")
        if sb_url and sb_key:
            print(f"✓ Supabase configured ({sb_url[:40]}...)")
        else:
            print("✗ Supabase not configured")
            print("  Set SUPABASE_URL and SUPABASE_KEY")

        # Check contracts
        contracts_dir = "src/trading_bot/contracts"
        required_files = ["risk_model.yaml", "data_contract.yaml", "execution_contract.yaml"]
        from pathlib import Path
        contracts_path = Path(contracts_dir)
        if contracts_path.exists():
            found = [f for f in required_files if (contracts_path / f).exists()]
            print(f"✓ Contracts directory: {len(found)}/{len(required_files)} files found")
            for f in required_files:
                status = "✓" if (contracts_path / f).exists() else "✗"
                print(f"  {status} {f}")
        else:
            print(f"✗ Contracts directory not found: {contracts_dir}")

        return


if __name__ == "__main__":
    main()
