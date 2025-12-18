from __future__ import annotations

import argparse
from pathlib import Path
from trading_bot.log.event_store import EventStore

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/events.db")
    p.add_argument("--schema", default=str(Path(__file__).resolve().parents[1] / "log" / "schema.sql"))
    args = p.parse_args()

    store = EventStore(args.db)
    store.init_schema(args.schema)
    print(f"Initialized {args.db}")

if __name__ == "__main__":
    main()
