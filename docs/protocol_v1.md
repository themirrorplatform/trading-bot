# Bot ↔ Execution Bridge Protocol v1

Version: 1
Date: 2025-12-18
Scope: Local-only, deterministic command/event contract for execution adapters (Tradovate, NinjaTrader) without changing bot logic.

## Envelope

```json
{
  "v": 1,
  "ts": "2025-12-18T03:12:45.123Z",
  "type": "Command.EnterLimit",
  "decision_id": "D-20251218-031245-ES-000193",
  "correlation_id": "C-9f4e0e8a",
  "payload": {}
}
```

- `v`: protocol version
- `ts`: ISO8601 in UTC
- `type`: message type (see below)
- `decision_id`: bot decision reference
- `correlation_id`: optional tracing id
- `payload`: message body

## Commands (bot → bridge)

### Command.EnterLimit
```json
{
  "account": "SIM101",
  "instrument": "ES 03-26",
  "side": "BUY",
  "qty": 3,
  "limit_price": 6075.25,
  "time_in_force": "DAY",
  "ttl_ms": 45000,
  "bracket": {
    "stop_price": 6068.75,
    "target_price": 6088.25,
    "target_qty": 2
  },
  "meta": { "edge": 0.63, "euc": 0.12, "dvs": 0.95, "eqs": 0.90 }
}
```

### Command.EnterStopLimit
```json
{
  "account": "SIM101",
  "instrument": "ES 03-26",
  "side": "SELL",
  "qty": 2,
  "stop_price": 6072.00,
  "limit_price": 6071.75,
  "ttl_ms": 30000,
  "bracket": { "stop_price": 6078.50, "target_price": 6059.50, "target_qty": 1 }
}
```

### Command.Replace
```json
{ "order_id": "NT-ORD-12345", "new_limit_price": 6075.00, "new_stop_price": null, "new_qty": null }
```

### Command.Cancel
```json
{ "order_id": "NT-ORD-12345" }
```

### Command.Flatten
```json
{ "account": "SIM101", "instrument": "ES 03-26" }
```

## Events (bridge → bot)

### Event.OrderState
```json
{ "order_id": "NT-ORD-12345", "state": "WORKING", "reason": null }
```

States: `ACCEPTED`, `WORKING`, `PARTIALLY_FILLED`, `FILLED`, `CANCELED`, `REJECTED`.

### Event.ExecutionReport
```json
{
  "order_id": "NT-ORD-12345",
  "fill_id": "NT-FILL-8891",
  "filled_qty": 1,
  "fill_price": 6075.25,
  "remaining_qty": 2,
  "commission": 1.18,
  "slippage_ticks": 1
}
```

### Event.PositionUpdate
```json
{ "instrument": "ES 03-26", "position_qty": 3, "avg_price": 6075.17, "unrealized_pnl": 125.00 }
```

## Lifecycle hooks (NinjaTrader mapping)
- OnOrderUpdate → Event.OrderState
- OnExecutionUpdate → Event.ExecutionReport (attach/maintain brackets)
- OnPositionUpdate → Event.PositionUpdate
- Connection status callback → health/kill-switch

## Determinism & IDs
- `decision_id` → `order_group_id` → `order_id` must be preserved in all events.
- Bridge should not make decisions; it executes and reports.

## Safety rules
- No market entries; only `EnterLimit` / `EnterStopLimit` accepted
- Bracket required (OCO); if bracket fails, cancel entry
- TTL enforced; expire and cancel
- Kill switch on disconnect or event stall
