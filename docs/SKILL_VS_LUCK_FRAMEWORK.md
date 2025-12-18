# Skill vs Luck Framework: Learning Without Lying to Yourself

Version: 1.0.0

Core Principle: Outcome ≠ Proof. The bot must never confuse "I won" with "I was right."

---

## THE FUNDAMENTAL INSIGHT

Traditional learning: winner = good, loser = bad

Our learning: outcome updates performance, process updates theory

A "lucky win" is not evidence of skill. A "unlucky loss" is not evidence of error.
The bot must compute this explicitly, not hope it averages out.

---

## PART 1: THE THREE SCORES

Every trade receives three independent scores:

- Edge Score: ex-ante decision quality derived from beliefs and EUC scoring
- Luck Score: path/outcome surprise relative to expected path distribution
- Execution Score: how closely fills and order states matched intent and constraints

### 1. Edge Score (0..1)
- What it measures: The probability-weighted quality of the setup at entry time.
- Inputs: Constraint beliefs (e.g., F1..Fn), applicability gates, DVS/EQS, EUC components.
- Example mapping: Edge = Belief(F*) × TemplateQuality × TierGate × StabilityHaircut.
- In practice: Use the decision module’s EUC Edge component or an equivalent belief-to-edge mapping.

### 2. Luck Score (0..1)
- What it measures: How surprising the realized path/outcome was given the entry hypothesis.
- Inputs: Did price almost stop then reverse? Path-to-target vs path-to-stop odds, volatility shocks, gaps.
- Heuristics (examples):
  - If the trade barely missed the stop (≤ 1–2 ticks) then ran to target → high Luck.
  - If the trade moved directly to target through expected path → low Luck.
  - If an exogenous event (halt/disconnect) altered path → treat as high Luck.

### 3. Execution Score (0..1)
- What it measures: Did the platform give us what we asked for?
- Inputs: Slippage vs estimate, spread at entry, bracket placement latency, rejected/canceled states.
- Typical features:
  - SlippageScore = max(0, 1 − (actual_slippage / worst_case))
  - SpreadScore = max(0, 1 − (spread_ticks / max_spread_allowed))
  - BracketScore = 1 if OCO stop/target attached on fill within latency budget; else < 1

---

## PART 2: THE LEARNING WEIGHT

Definition: LearningWeight = (1 − LuckScore) × ExecutionScore

Interpretation:
- Downweights outcomes that were likely driven by randomness.
- Zeroes-out learning when execution is untrustworthy.
- Keeps theory updates focused on skill signals, not accidents.

Recommended ranges:
- Lucky win: Luck≈0.7, Exec≈0.95 → Weight ≈ 0.285 → light update
- Clean loss: Luck≈0.1, Exec≈0.95 → Weight ≈ 0.855 → strong update
- Messy fill: Exec≈0.3 → Weight small regardless of luck

---

## PART 3: VERDICTS (PROCESS VS OUTCOME)

- Good decision, earned outcome: high Edge, low Luck, high Exec
- Good decision, lucky outcome: high Edge, high Luck, high Exec
- Bad decision, deserved outcome: low Edge, low Luck, high Exec
- Bad decision, got away with it: low Edge, high Luck, high Exec
- Contaminated execution: any with low Exec → deprioritize outcome learning

Use these to label trades for dashboards and post-mortems. They do not alter the historical record; they clarify it.

---

## PART 4: ATTRIBUTION PIPELINE IN THIS REPO

- Event Types (see [src/trading_bot/core/types.py](src/trading_bot/core/types.py)):
  - DECISION_RECORD: one per cycle (journal)
  - ATTRIBUTION: one per trade close (post-trade analysis)

- Decision Journal (see [src/trading_bot/log/decision_journal.py](src/trading_bot/log/decision_journal.py)):
  - Summarizes each cycle in plain language and structured form

- Attribution Engine (v2 skeleton wired via runner):
  - Computes Edge/Luck/Execution and LearningWeight
  - Emits ATTRIBUTION events upon fills/closures

- Where scores come from:
  - Edge: decision engine belief/EUC
  - Luck: realized path features (near-stop-first, gap, reversal metrics)
  - Execution: adapter feedback (slippage/spread/latency, reject/cancel)

---

## PART 5: STATISTICAL CAUTION

- Do not use realized PnL to directly update signal weights.
- Use LearningWeight to scale updates; cap per-trade maximum influence.
- Bucket observations by regime; do not blend RTH vs ETH or volatile vs calm blindly.

---

## PART 6: IMPLEMENTATION NOTES

- Determinism: All scores must be derivable from logged state; no lookahead.
- Idempotency: Recomputations must reproduce the same ATTRIBUTION event_id for the same inputs.
- Extensibility: Add more path features and refine luck later without breaking event schemas.

---

## PART 7: EXAMPLES

Example 1 — Lucky Win
- Edge: 0.72, Luck: 0.68, Exec: 0.94 → Weight = 0.30
- Verdict: Good decision, lucky outcome
- Action: Keep hypothesis; minimal parameter reinforcement

Example 2 — Clean Loss
- Edge: 0.65, Luck: 0.12, Exec: 0.96 → Weight = 0.84
- Verdict: Good decision, earned loss
- Action: Strengthen risk estimates; no penalty to signal weights

---

## PART 8: ROADMAP

- Expand luck heuristics (drawdown depth before win, time-to-target vs expectation, path curvature)
- Richer execution scoring (partial fill handling, ATM latency audit)
- Learning kernel (EWMA with caps) integrating LearningWeight across setups and regimes
