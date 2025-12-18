# Decision Journal: Every Decision Explained

Version: 1.0.0

Core Principle: The bot must explain every decision, including (especially) no-trades.

---

## PURPOSE

The Decision Journal is an append-only event stream where every cycle produces exactly one record.

It serves three functions:

1. Audit Trail — Complete forensic record of what the bot saw and decided
2. Learning Input — Structured data for attribution and parameter updates
3. Human Understanding — Plain English explanations for every decision

---

## THE DECISION RECORD

Event type: DECISION_RECORD

Schema (see [src/trading_bot/log/decision_journal.py](src/trading_bot/log/decision_journal.py)):
- time: iso8601 string (UTC or consistent timezone policy)
- instrument: stream id (e.g., MES_RTH)
- action: ENTER | HOLD | EXIT | MODIFY | SKIP
- setup_scores: map of setup/belief IDs to scores (e.g., {"F1": 0.72})
- euc_score: EUC total if available (v2+); null otherwise
- reasons: structured reason codes and metrics
- plain_english: concise human-readable summary
- context: dvs, eqs, session_phase, friction, spread, etc.

Example JSON:
```json
{
  "time": "2025-12-18T14:01:00-05:00",
  "instrument": "MES_RTH",
  "action": "SKIP",
  "setup_scores": {"F1": 0.58, "F3": 0.21},
  "euc_score": null,
  "reasons": {"reason_code": "FRICTION_TOO_HIGH", "details": {"spread_ticks": 2, "slippage_ticks": 1}},
  "plain_english": "Skipped: FRICTION_TOO_HIGH; spread_ticks=2; dvs=0.93; eqs=0.91; setups=(F1:0.58, F3:0.21)",
  "context": {"dvs": 0.93, "eqs": 0.91, "session_phase": 3, "spread_ticks": 2}
}
```

---

## EMISSION RULES

- Exactly once per decision cycle.
- Emitted regardless of action (including SKIP).
- Derived from the same inputs used to decide (signals, state, risk_state).

---

## REASONS & GRAMMAR

A consistent reason grammar makes both machines and humans happy:

Reason = (Code, metric, threshold, comparator, context)

Examples:
- EUC_TOO_LOW; euc=-0.08<th=0.00; edge=0.61; unc=0.52; cost=0.17
- SESSION_BLOCK; now=12:03; allowed=09:35-11:30
- FRICTION_TOO_HIGH; friction=$9>max=$4.75
- UNCERTAINTY_TOO_HIGH; unc=0.71>max=0.60

The runner maps engine outputs and thresholds into `reasons.details`.

---

## WHERE IT’S WIRED

- Runner: one record per cycle in [src/trading_bot/core/runner.py](src/trading_bot/core/runner.py)
- Implementation: see `DecisionJournal.log()` and helpers `summarize_no_trade()` / `summarize_trade()`
- Event store: [src/trading_bot/log/event_store.py](src/trading_bot/log/event_store.py)

---

## COUNTERFACTUALS (OPTIONAL EXTENSION)

Add a `counterfactual` object when helpful:
- next_best_action: what would have triggered an entry
- minimal_change: smallest metric change to flip the decision
- gates_failed: array of failed gates with thresholds

These help explain near-miss decisions and guide threshold tuning.

---

## OPERATIONAL NOTES

- Determinism: The same inputs should produce the same DecisionRecord ID.
- Cost: Keep summaries short; this is a hot path.
- Privacy: Avoid personally identifying info in plain_english.
