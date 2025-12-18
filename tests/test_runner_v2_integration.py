import json
from decimal import Decimal
from datetime import datetime

import pytest

# Ensure tzdata is available for ZoneInfo("America/New_York") used by engines
pytest.importorskip("tzdata")

from src.trading_bot.core.runner import BotRunner
from src.trading_bot.log.event_store import EventStore


@pytest.mark.integration
def test_runner_v2_emits_beliefs_and_decision(tmp_path):
    db_path = tmp_path / "events.sqlite"
    runner = BotRunner(db_path=str(db_path))

    bar = {
        "ts": "2025-12-18T10:00:00-05:00",
        "o": 5600.00,
        "h": 5601.00,
        "l": 5599.00,
        "c": 5600.50,
        "v": 1200,
    }

    decision = runner.run_once(bar, stream_id="MES_RTH")
    assert decision["action"] in ("ORDER_INTENT", "NO_TRADE")

    store = EventStore(str(db_path))
    events = store.read_stream("MES_RTH")
    types = [e.type for e in events]

    assert "BELIEFS_1M" in types
    assert "DECISION_1M" in types
    # Ensure decision payload is JSON-serializable
    json.dumps(decision)
