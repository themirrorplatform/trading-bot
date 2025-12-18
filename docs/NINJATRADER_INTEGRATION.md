# NinjaTrader Integration: Architecture Options

Version: 1.0.0

Decision Required: Choose architecture before implementation

---

## WHY NINJATRADER?

For MES futures execution with brackets, stops, targets, and runners, NinjaTrader 8 is a strong choice because:

1. Robust order lifecycle hooks — OnOrderUpdate / OnExecutionUpdate for managing stops/targets on fills
2. Built-in bracket/OCO behavior — Managed approach ties protective orders to entries
3. ATM templates — Standardized stop/target/trailing behavior
4. Broad connectivity — Works with multiple brokers and data feeds
5. Deterministic execution — Matches "execution must be real, inspectable" philosophy

---

## ARCHITECTURE OPTIONS

- Option A — Bot inside NT (C# strategy only)
  - Pros: Single runtime; direct API; simplest lifecycle
  - Cons: Rewrites Python engines; limits experimentation; less flexible

- Option B — Hybrid: Python brain + NinjaTrader hands (recommended)
  - Pros: Keep Python research stack; NT handles orders & OCO; decouple thinking from execution
  - Cons: Requires local bridge (HTTP/WebSocket) and message contracts

---

## MESSAGE CONTRACTS (v1)

See: [docs/protocol_v1.md](protocol_v1.md)

- Commands (bot → NT): EnterLimit, EnterStopLimit, Replace, Cancel, Flatten
- Events (NT → bot): OrderState, ExecutionReport, PositionUpdate
- Determinism: decision_id → order_group_id → order_id preserved across all messages
- Safety rules: no market entries; bracket required; TTL; kill-switch on disconnect/stall

---

## NT LIFECYCLE HOOKS

- OnOrderUpdate → send Event.OrderState
- OnExecutionUpdate → send Event.ExecutionReport; attach/maintain OCO brackets here
- OnPositionUpdate → send Event.PositionUpdate
- ConnectionStatusUpdate → kill-switch if disconnected
- Timer/heartbeat → periodic reconciliation and health

Note: Drive fill logic off OnExecutionUpdate, not OnOrderUpdate, per NT guidance.

---

## ADD-ON SKELETON

A minimal local-only bridge (HTTP) scaffold is provided:

- Location: bridges/ninjatrader/AddOnSkeleton.cs
- Endpoints: POST /command, GET /events (long-poll)
- Auth: X-Auth-Token header; bind to 127.0.0.1
- Behavior: Execute commands on NT threads; enqueue events for bot to poll

---

## CHECKLIST FOR IMPLEMENTATION

- [ ] Confirm architecture (Option B recommended)
- [ ] Implement command handlers → NT API calls
- [ ] Emit events from NT hooks → bridge queue
- [ ] Add TTL/job watchdog on entries; cancel/flatten on failure
- [ ] Reconciliation loop: compare NT orders/positions to bot expectations; halt on mismatch
- [ ] End-to-end test in SIM: verify OCO attachment and partial fills

---

## TRADE-OFFS

- Latency: Local HTTP/WebSocket is sufficiently low for minute bars; per-tick users may consider in-process integration
- Robustness: NT manages OCO; bridge remains stateless and dumb (executor only)
- Maintainability: Python core stays intact; execution venue can be swapped later
