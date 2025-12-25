from __future__ import annotations
import argparse
import json
import os
import sys
import logging
from pathlib import Path
from trading_bot.log.event_store import EventStore
from trading_bot.core.runner import BotRunner
from trading_bot.tools.replay_runner import replay_stream, replay_json
from trading_bot.core.types import Event
from trading_bot.core.types import stable_json, sha256_hex
from trading_bot.core.config import load_yaml_contract
from trading_bot.core.adapter_factory import create_adapter
from decimal import Decimal
from datetime import datetime, timedelta, timezone
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
    # LIVE adapter options
    s_run.add_argument("--live", action="store_true", help="Use live Tradovate adapter")
    s_run.add_argument("--account-id", type=int, help="Broker account id (LIVE)")
    s_run.add_argument("--access-token", help="Broker access token (LIVE)")
    s_run.add_argument("--ws-url", help="Websocket URL (LIVE)")
    s_run.add_argument("--instrument", default="MES", help="Instrument symbol (LIVE)")
    s_run.add_argument("--heartbeat-interval", type=int, default=10)
    s_run.add_argument("--reconnect-interval", type=int, default=20)
    s_run.add_argument("--poll-interval", type=int, default=5)

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

    # adapter demo (SIM): exercise TTL and modification budget
    s_demo = sub.add_parser("adapter-demo")
    s_demo.add_argument("--fill-mode", default="TIMEOUT", choices=["IMMEDIATE", "DELAYED", "PARTIAL", "TIMEOUT"], help="SIM fill mode")
    s_demo.add_argument("--limit-price", type=float, default=5600.50)
    s_demo.add_argument("--contracts", type=int, default=1)
    s_demo.add_argument("--direction", choices=["LONG", "SHORT"], default="LONG")
    s_demo.add_argument("--ttl-seconds", type=int, default=90)

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
    s_kill.add_argument("--db", default="data/events.sqlite")

    # sync - Force sync to Supabase
    s_sync = sub.add_parser("sync", help="Force sync events to Supabase")
    s_sync.add_argument("--db", default="data/events.sqlite")

    # verify-config - Verify Tradovate and Supabase credentials
    s_verify = sub.add_parser("verify-config", help="Verify API credentials")

    # evolve - Run evolution engine to learn from trades
    s_evolve = sub.add_parser("evolve", help="Run evolution engine to learn from trades")
    s_evolve.add_argument("--db", default="data/events.sqlite")
    s_evolve.add_argument("--contracts", default="src/trading_bot/contracts")
    s_evolve.add_argument("--force", action="store_true", help="Override weekly cadence check")
    s_evolve.add_argument("--dry-run", action="store_true", help="Show proposed changes without applying")

    # show-params - Show current learned parameters
    s_params = sub.add_parser("show-params", help="Show current learned parameters")

    args = p.parse_args()

    if args.cmd == "init-db":
        store = EventStore(args.db)
        store.init_schema(args.schema)
        print(f"Initialized DB at {args.db}")
        return

    if args.cmd == "run-once":
        with open(args.bar_json, "r", encoding="utf-8") as f:
            bar = json.load(f)
        adapter_kwargs = {}
        if args.live and args.adapter == "tradovate":
            adapter_kwargs = {
                "mode": "LIVE",
                "account_id": args.account_id,
                "access_token": args.access_token,
                "ws_url": args.ws_url,
                "instrument": args.instrument,
                "heartbeat_interval": args.heartbeat_interval,
                "reconnect_interval": args.reconnect_interval,
                "poll_interval": args.poll_interval,
            }
        runner = BotRunner(db_path=args.db, adapter=args.adapter, fill_mode=args.fill_mode, adapter_kwargs=adapter_kwargs)
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

    if args.cmd == "adapter-demo":
        # Construct SIM adapter with TIMEOUT to avoid immediate fills
        adapter = create_adapter("tradovate", fill_mode=args.fill_mode)

        class _IntentObj:
            def __init__(self, d):
                for k, v in d.items():
                    setattr(self, k, v)

        # Build a simple intent with bracket
        ts = datetime.now(timezone.utc)
        tick_size = 0.25
        stop_ticks = 8
        target_ticks = 12
        side = 1 if args.direction == "LONG" else -1
        stop_price = args.limit_price - side * stop_ticks * tick_size
        target_price = args.limit_price + side * target_ticks * tick_size
        intent = _IntentObj({
            "timestamp": ts,
            "direction": args.direction,
            "contracts": args.contracts,
            "stop_ticks": stop_ticks,
            "target_ticks": target_ticks,
            "entry_type": "LIMIT",
            "metadata": {
                "limit_price": args.limit_price,
                "bracket": {
                    "stop_price": round(stop_price, 2),
                    "target_price": round(target_price, 2),
                    "target_qty": max(1, args.contracts),
                }
            }
        })

        print("Placing order...")
        res = adapter.place_order(intent, Decimal(str(args.limit_price)))
        print(json.dumps(res, indent=2))
        oid = res.get("order_id")

        if not oid:
            print("No order_id returned; demo aborted.")
            return

        print("Replace #1 (limit +0.50)...")
        r1 = adapter.replace_order(oid, {"limit_price": args.limit_price + 0.50})
        print(json.dumps(r1, indent=2))

        print("Replace #2 (limit -0.25)...")
        r2 = adapter.replace_order(oid, {"limit_price": args.limit_price + 0.25})
        print(json.dumps(r2, indent=2))

        print("Replace #3 (should fail due to cap)...")
        r3 = adapter.replace_order(oid, {"limit_price": args.limit_price})
        print(json.dumps(r3, indent=2))

        print("Attempt cancel (may fail if cap reached)...")
        ok = adapter.cancel_order(oid)
        print(json.dumps({"cancel_ok": ok}, indent=2))

        print("Advancing time to enforce TTL...")
        future = ts + timedelta(seconds=max(1, args.ttl_seconds + 1))
        adapter.on_cycle(future, ttl_seconds=args.ttl_seconds)

        print("Open orders snapshot:")
        print(json.dumps(adapter.get_open_orders(), indent=2))
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

    if args.cmd == "evolve":
        print("Running Evolution Engine...")
        print("-" * 40)

        from trading_bot.engines.evolution import create_evolution_engine

        engine = create_evolution_engine(
            db_path=args.db,
            contracts_path=args.contracts,
        )

        result = engine.run_evolution(
            force=args.force,
            dry_run=args.dry_run,
        )

        print(f"\nResult: {result.reason}")
        print(f"Trades analyzed: {result.trades_analyzed}")
        print(f"Parameters updated: {result.parameters_updated}")

        if result.changes:
            print("\nChanges:")
            for key, change in result.changes.items():
                if isinstance(change, dict) and "old" in change:
                    print(f"  {key}: {change['old']:.4f} -> {change['new']:.4f} (Δ{change['delta']:+.4f})")
                else:
                    print(f"  {key}: {change}")

        if args.dry_run:
            print("\n(Dry run - no changes applied)")

        return

    if args.cmd == "show-params":
        print("Learned Parameters")
        print("-" * 40)

        params_path = Path("data/learned_params.json")
        if not params_path.exists():
            print("No learned parameters found.")
            print("Run 'evolve' command to generate parameters from trades.")
            return

        with open(params_path, "r") as f:
            params = json.load(f)

        print(f"\nVersion: {params.get('version', 0)}")
        print(f"Last updated: {params.get('last_updated', 'Never')}")
        print(f"Update reason: {params.get('update_reason', 'N/A')}")

        print("\nSignal Weights:")
        for constraint_id, signals in params.get("signal_weights", {}).items():
            print(f"  {constraint_id}:")
            for signal, weight in signals.items():
                print(f"    {signal}: {weight:.3f}")

        print("\nBelief Thresholds:")
        for constraint_id, threshold in params.get("belief_thresholds", {}).items():
            print(f"  {constraint_id}: {threshold:.3f}")

        print("\nDecay Rates:")
        for constraint_id, rate in params.get("decay_rates", {}).items():
            print(f"  {constraint_id}: {rate:.3f}")

        return


if __name__ == "__main__":
    main()
