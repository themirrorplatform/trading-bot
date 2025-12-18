from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path

from src.trading_bot.log.event_store import EventStore
from src.trading_bot.log.decision_journal import DecisionJournal, DecisionRecord
from src.trading_bot.engines.attribution_v2 import score_post_trade


def test_decision_journal_appends(tmp_path: Path):
    db = tmp_path / "events.sqlite"
    store = EventStore(str(db))
    store.init_schema("src/trading_bot/log/schema.sql")

    journal = DecisionJournal(store=store, stream_id="SIM:MES", config_hash="testhash")
    rec = DecisionRecord(
        time=datetime.now(timezone.utc).isoformat(),
        instrument="MES",
        action="SKIP",
        setup_scores={"F1": 0.72, "F3": 0.41},
        euc_score=None,
        reasons={"reason_code": "EQS_BELOW_ENTRY_THRESHOLD", "details": {"eqs": 0.7, "threshold": 0.75}},
        plain_english=DecisionJournal.summarize_no_trade({"F1":0.72},{"reason_code":"EQS_BELOW_ENTRY_THRESHOLD","details":{"eqs":0.7}}, {"dvs":0.95,"eqs":0.70,"session_phase":1}),
        context={"dvs": 0.95, "eqs": 0.70, "session_phase": 1, "friction_usd": 9.0},
    )
    ok = journal.log(rec)
    assert ok is True

    events = store.read_stream("SIM:MES")
    assert any(e.type == "DECISION_RECORD" for e in events)


def test_attribution_v2_scores():
    trade = {
        "forecast": {"expected_return_ticks": 10, "belief_probability": 0.6, "friction_usd": 9.0},
        "plan": {"stop_ticks": 8, "target_ticks": 12, "expected_time_to_target_s": 1200},
        "path": {"mae_ticks": 2, "mfe_ticks": 10, "time_to_hit_s": 800, "hit": "target"},
        "execution": {"slippage_ticks": 0.5, "spread_ticks": 1, "partial_fill": False, "rejects": 0},
        "pnl_usd": 25.0,
    }
    scores = score_post_trade(trade)
    assert 0.0 <= scores.edge_score <= 1.0
    assert 0.0 <= scores.luck_score <= 1.0
    assert 0.0 <= scores.execution_score <= 1.0
    assert 0.0 <= scores.learning_weight <= 1.0
    assert isinstance(scores.classification, str)
