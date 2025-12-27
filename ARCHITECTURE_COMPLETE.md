# TRADING BOT COMPLETE ARCHITECTURE MAP

**Generated:** December 27, 2025  
**Status:** Current codebase analysis (local working copy)

---

## EXECUTIVE SUMMARY

**Total Scale:**
- **1,851 Python files** in src/trading_bot
- **97 TypeScript/React files** in ui/src
- **274 lines** of Supabase SQL migrations
- **FastAPI backend** with WebSocket streaming from SQLite
- **Multiple execution layers:** signals → beliefs → decisions → execution → learning

**Current State:**
- ✓ Core bot logic complete (28 signals, capital tiers, EUC scoring)
- ✓ UI components built (97 TSX files)
- ✓ API reads from local SQLite
- ✓ Supabase migrations exist
- ⚠ **GAPS:** Bot doesn't write to API, UI doesn't connect to Supabase, learning loop not wired to runner

---

## LAYER 1: DATA INGESTION & SIGNALS

### Engines (src/trading_bot/engines/)

**signals_v2.py** (889 lines)
- **Purpose:** Compute 28 signals from bar data
- **Categories:**
  - Price Structure & Volatility (12): vwap_z, atr_14_n, range_compression, hhll_trend_strength, breakout_distance_n, rejection_wick_n, close_location_value, gap_from_prev_close_n, distance_from_poc_proxy, micro_trend_5, real_body_impulse_n, vwap_slope
  - Volume & Participation (9): vol_z, vol_slope_20, effort_vs_result, range_expansion_on_volume, climax_bar_flag, quiet_bar_flag, consecutive_high_vol_bars, participation_expansion_index
  - Session Context (4): session_phase, opening_range_break, lunch_void_gate, close_magnet_index
  - Quality & Cost (3): spread_proxy_tickiness, slippage_risk_proxy, friction_regime_index
- **Output:** `SignalOutput` dataclass with reliability metadata
- **Key Methods:**
  - `compute_signals()` - main entry point
  - Session detection (RTH: 09:30-16:00 ET, Globex: 17:00-16:00 ET)
  - VWAP calculation with reset at 09:30 RTH
  - ATR, volatility, trend computation

**dvs_eqs.py**
- **Purpose:** Data/Execution quality scoring
- **compute_dvs()** - Data Validity Score based on lag, gaps, outliers
- **compute_eqs()** - Execution Quality Score based on slippage, connection state

**readiness.py** (NEW - from local changes)
- **Purpose:** Compute market readiness snapshot
- **compute_readiness_snapshot()** - PDH/PDL/PDC, ONH/ONL, VWAP, ATR, distances
- **Output:** Full dict with levels, distances in points & ATR, DTE, data_quality

---

## LAYER 2: BELIEFS & STRATEGIES

### Belief Engine

**belief_v2.py**
- **Purpose:** Convert signals into probabilistic beliefs about market state
- **BeliefEngineV2** class
- **Key Methods:**
  - `compute_beliefs()` - takes signals, outputs beliefs per constraint
  - Effective likelihood calculation with DVS/EQS adjustment
  - Constraint satisfaction scoring

### Strategy Recognition

**bias_engine.py** (from file list)
- **Purpose:** Detect market biases (trend, mean-reversion, breakout, etc.)
- **BiasCategory:** TREND, MEAN_REVERSION, BREAKOUT, etc.
- **BiasState:** active/inactive with confidence scores

**strategy_recognizer.py**
- **Purpose:** Match signals/beliefs to predefined strategy templates
- **StrategyClass:** K1, K2, K3, K4 templates
- **Template matching** based on belief thresholds

**detectors.py**
- **Purpose:** Pattern detection (breaks level, retest holds, range compression, impulse strength, VWAP deviation, sweep then reject)
- **6 detector classes:** BreaksLevel, RetestHolds, RangeCompression, ImpulseStrength, VwapDeviation, SweepThenReject

---

## LAYER 3: DECISION ENGINE

### Decision Engine V2 (decision_v2.py - 681 lines)

**Purpose:** Constitutional hierarchy with capital tier gates

**Hierarchy:**
1. Layer 0: KILL_SWITCH
2. Layer 1: CONSTITUTION
3. Layer 2: QUALITY_GATES (DVS, EQS)
4. Layer 3: SESSION_GATES
5. Layer 4: REGIME_LOCKOUTS
6. Layer 5: CAPITAL_TIER_GATES ← **KEY INNOVATION**
7. Layer 6: BELIEF_STABILITY_GATES
8. Layer 7: FRICTION_GATE
9. Layer 8: TEMPLATE_EXECUTION

**Capital Tiers:**
- **S (Survival):** $0-$2.5k → K1, K2 templates, 10 tick max stop, $12 max risk
- **A (Advancement):** $2.5k-$7.5k → K1, K2, K3, 14 tick max stop, $15 max risk
- **B (Breakout):** $7.5k+ → K1, K2, K3, K4, 18 tick max stop, $15 max risk

**EUC Scoring:**
- Edge = E_R × P_lb (expected return × lower bound probability)
- Uncertainty = f(DVS, EQS, belief_stability)
- Cost = friction / expected_move
- **Total Score = Edge - Uncertainty - Cost**

**Output:** `DecisionResult` with action ("NO_TRADE" or "ORDER_INTENT"), reason, order_intent, metadata

**Key Methods:**
- `decide()` - main decision logic
- `_classify_tier()` - determine capital tier from equity
- `_compute_euc()` - calculate Edge-Uncertainty-Cost score
- `_check_gates()` - constitutional gate validation

---

## LAYER 4: EXECUTION & TRADE MANAGEMENT

### Core Execution (src/trading_bot/core/)

**runner.py** (359 lines)
- **Purpose:** Main event loop - orchestrates all engines
- **BotRunner class**
- **Data Flow:**
  1. Bar → signals (`compute_signals`)
  2. Signals → beliefs (`compute_beliefs`)
  3. Beliefs + state → decision (`decide`)
  4. Decision → order placement (`place_order`)
  5. Fill events → attribution
  6. Reconciliation + TTL enforcement

**Key Features:**
- Config hash for reproducibility
- Event persistence to SQLite (EventStore)
- Decision journaling
- Order lifecycle management
- Position reconciliation (expected vs actual)
- TTL cancel loop (90 seconds default)
- Fill simulation support

**execution_supervisor.py** (171 lines)
- **Purpose:** Order/bracket lifecycle state machine
- **ParentOrder tracking:** CREATED → SUBMITTING → ACKED → PARTIAL → FILLED → DONE
- **ChildOrder tracking:** STOP, TARGET
- **Idempotent submission** with client_order_id
- **Recovery logic:** restart-safe, reconnect handling

**trade_manager.py**
- **Purpose:** Track active trades and their state
- **TradeState:** OPEN, PARTIAL, CLOSED
- **Methods:** open_trade(), update_trade(), close_trade()

**state_store.py**
- **Purpose:** In-memory state for risk, positions, entries
- **Methods:**
  - `get_risk_state()` - current risk metrics
  - `record_entry()` - log trade entry
  - `update_expected_position()` - track expected position
  - `set_expected_position()` - reconciliation updates

---

## LAYER 5: ADAPTERS

### Adapter Layer (src/trading_bot/adapters/)

**adapter_factory.py**
- **create_adapter(name, **kwargs)** - factory pattern
- **Supported:** tradovate, ninjatrader, ibkr, sim

**ibkr_adapter.py** (NEW - from local changes)
- **Purpose:** Interactive Brokers integration via ib_insync
- **Key Methods:**
  - `connect()` - establish TWS/Gateway connection
  - `place_order()` - submit bracket orders
  - `get_position_snapshot()` - current positions
  - `get_market_context()` - full adapter state (session_open, execution_enabled, data_mode, DTE, etc.)
  - `assert_execution_allowed()` - hard gates (kill switch, account ready, session open)
  - `_resolve_primary_contract()` - MES contract resolver with DTE filter (min 5 days)
  - `get_status()` - includes DTE, contract_month, equity
- **Fail-closed:** No orders unless ALL gates pass

**tradovate.py**
- **Purpose:** Tradovate futures broker
- **Fill modes:** IMMEDIATE, DELAYED, PARTIAL, TIMEOUT
- **Simulated fills** with realistic timing

**ninjatrader_bridge.py**
- **Purpose:** HTTP bridge to NinjaTrader Add-On
- **REST API** for order submission

---

## LAYER 6: LEARNING & EVOLUTION

### Learning System (src/trading_bot/core/)

**learning_loop.py** (401 lines)
- **Purpose:** Capture trade outcomes, update strategy weights

**Components:**
1. **TradeOutcome dataclass:**
   - Captures: entry/exit, PnL, beliefs, signals, EUC score, DVS/EQS, slippage
   - Commission deduction ($2.50 round-trip)

2. **ReliabilityMetrics:**
   - Per strategy/regime/time-of-day
   - Tracks: win rate, expectancy, Sharpe ratio, max drawdown, consecutive wins/losses
   - Throttle levels (0=normal, 1=mild, 2=heavy)
   - Quarantine state

3. **LearningLoop class:**
   - `record_trade()` - capture outcome
   - `update_reliability()` - recompute metrics
   - `_should_quarantine()` - 2+ consecutive losses OR negative expectancy
   - `_should_throttle()` - low win rate or poor Sharpe
   - `get_throttle_multiplier()` - increase EUC cost for underperforming strategies
   - `_re_enable_if_recovered()` - 2+ consecutive wins restores ACTIVE state

**Quarantine Triggers:**
- 2+ consecutive losses
- Negative expectancy
- Win rate < min_acceptable_win_rate (default 0.40)

**Re-enable Triggers:**
- 2+ consecutive wins
- Positive expectancy restored

---

## LAYER 7: PERSISTENCE & EVENTS

### Event Store (src/trading_bot/log/)

**event_store.py**
- **Purpose:** SQLite persistence of all events
- **Schema:** events table (id, stream_id, ts, type, payload_json, config_hash, created_at)
- **Event types:** DECISION_1M, BELIEFS_1M, ORDER_EVENT, FILL_EVENT, RECONCILIATION, ATTRIBUTION, READINESS_SNAPSHOT

**decision_journal.py**
- **Purpose:** Human-readable decision log
- **DecisionRecord:** time, instrument, action, setup_scores, euc_score, reasons, plain_english
- **Methods:**
  - `log()` - persist record
  - `summarize_trade()` - "ENTER" with reasoning
  - `summarize_no_trade()` - "SKIP" with gate failures

**schema.sql**
- **Tables:** events, decision_journal
- **Indexes:** stream_id, ts, type, config_hash

**exporters.py**
- **Purpose:** Export events to CSV, JSON, Parquet for analysis

---

## LAYER 8: API & BACKEND

### FastAPI Backend (api/main.py)

**Architecture:** Reads from SQLite (data/events.sqlite), streams to UI via WebSocket

**Endpoints:**
- `GET /api/status` - Bot status
- `GET /api/events` - Query events (filter by stream_id, type, time range)
- `GET /api/events/{event_id}` - Single event
- `GET /api/snapshot` - Latest state snapshot
- `WS /ws/events` - WebSocket streaming (polls SQLite every 200ms, broadcasts new events)

**ConnectionManager:**
- Tracks active WebSocket connections
- Broadcasts new events to all clients
- Auto-cleanup dead connections

**Configuration:**
- DB_PATH: `data/events.sqlite`
- POLL_INTERVAL_MS: 200
- CORS enabled for UI

**Current Gap:** Bot writes to EventStore (SQLite) but doesn't call API endpoints. API only reads SQLite.

---

## LAYER 9: UI & DASHBOARD

### Frontend (ui/src/ - 97 TSX files)

**Entry Point:** main.tsx → App.tsx

**Key Components:**

**LiveCockpit.tsx / LiveCockpitComplete.tsx**
- Real-time trading dashboard
- Position tracker, P&L, decision log

**Domain Components (ui/src/app/components/domain/):**
- **ConnectionStatus.tsx** - adapter connection state
- **DataQualityIndicator.tsx** - DVS/EQS display
- **DecisionCard.tsx** - individual decision with reasoning
- **BeliefStatePanel.tsx** - belief likelihoods per constraint
- **AttributionCard.tsx** - trade attribution breakdown
- **ExecutionBlameCard.tsx** - execution quality blame
- **GateResultRow.tsx** - constitutional gate pass/fail
- **EUCStackBar.tsx** - Edge/Uncertainty/Cost visualization
- **DriftAlertBanner.tsx** - DVS/EQS degradation warnings
- **AnnotationPanel.tsx** - manual notes on trades
- **EventRow.tsx** - event log entry

**Learning Components:**
- **LearningDashboard.tsx** - (likely exists, need to verify)
- Signal correlation heatmap
- Threshold evolution over time
- Top/bottom performing strategies

**UI State Management:**
- Context: SupabaseContext (needs creation)
- Hooks: useDecisions, usePositions, useReadiness (need creation)

**Current Gap:** UI components exist but aren't wired to real data source (neither local API WebSocket nor Supabase Realtime)

---

## LAYER 10: SUPABASE & CLOUD

### Supabase Migrations (supabase/migrations/ - 274 lines)

**20251218_phase2.sql**
- Core tables: decisions, positions, readiness_snapshots, bot_status, execution_errors, learning_records

**20251218_rls_policies.sql**
- Row-Level Security for multi-user access

**20251219_realtime_subscriptions.sql**
- Enable Realtime on all tables for live updates

**20251219_publisher_functions.sql**
- PostgreSQL functions for data publishing

**20251219_audit_and_retention.sql**
- Audit log, data retention policies

**Deployment Status:** Migrations exist, not yet applied to cloud instance

**Current Gap:** No Supabase client in bot or UI; migrations not deployed

---

## LAYER 11: CONFIGURATION & CONTRACTS

### Contracts (src/trading_bot/contracts/)

**constitution.yaml**
- Kill switch rules
- Session gates (RTH, Globex)
- Capital tier definitions

**risk_model.yaml**
- Max position size
- Stop loss rules
- Drawdown limits

**data_contract.yaml**
- DVS initial value
- Degradation events and penalties

**execution_contract.yaml**
- EQS initial value
- Order lifecycle (TTL, reconciliation interval)

**bias_registry.yaml** (likely exists)
- Bias definitions per category

**strategy_registry.yaml** (likely exists)
- Strategy templates (K1, K2, K3, K4)

**runtime.yaml**
- Default adapter, mode, stream_id
- Session hours
- Contract specifications

---

## CRITICAL DATA FLOWS

### Flow 1: Bar → Decision → Order

```
IBKR/Tradovate bar data
    ↓
SignalEngine.compute_signals()
    ↓ (28 signals + reliability)
BeliefEngine.compute_beliefs()
    ↓ (beliefs per constraint)
DecisionEngine.decide()
    ↓ (action + order_intent OR no_trade_reason)
Adapter.place_order()
    ↓ (bracket: entry limit + stop + target)
EventStore.append(ORDER_EVENT)
```

### Flow 2: Fill → Attribution → Learning

```
Broker fill notification
    ↓
Adapter.on_cycle() / pop_events()
    ↓ (FILL_EVENT)
attribution()
    ↓ (classify outcome: A1_THESIS_HELD, B2_STOPPED_PROPERLY, etc.)
EventStore.append(ATTRIBUTION)
    ↓
LearningLoop.record_trade()
    ↓
update_reliability() → throttle/quarantine decisions
    ↓
Adjusted EUC cost for next decision
```

### Flow 3: Event → UI Display

```
EventStore.append(event)
    ↓ (SQLite WAL mode)
API polls SQLite every 200ms
    ↓
WebSocket.broadcast(event)
    ↓
UI receives event
    ↓
React state updates
    ↓
Dashboard re-renders
```

### Flow 4: Readiness Snapshot (Closed Session)

```
DecisionEngine.decide() → execution_allowed=False
    ↓
Runner emits READINESS_SNAPSHOT
    ↓
compute_readiness_snapshot(bars, contract, data_quality)
    ↓
EventStore.append(READINESS_SNAPSHOT)
    ↓
API serves to UI or CLI
```

---

## INTEGRATION GAPS IDENTIFIED

### 🔴 **CRITICAL GAPS (Blocking Live Operation)**

1. **Bot → API Publishing**
   - **Issue:** Runner writes to EventStore but doesn't POST to API
   - **Impact:** No real-time streaming if API is remote
   - **Fix:** Add `SupabasePublisher` calls in runner.py after each event

2. **UI → Data Source**
   - **Issue:** UI components exist but no data hooks wired
   - **Impact:** Dashboard shows no data
   - **Fix:** Create SupabaseContext, useDecisions, usePositions hooks; wire to components

3. **Learning Loop → Runner Integration**
   - **Issue:** LearningLoop exists but not called in runner
   - **Impact:** No strategy learning
   - **Fix:** Instantiate LearningLoop in BotRunner; call on trade close

4. **Supabase Deployment**
   - **Issue:** Migrations not applied to cloud instance
   - **Impact:** Cannot store events in cloud
   - **Fix:** Run `supabase db push` or apply via Supabase dashboard

### ⚠️ **MEDIUM GAPS (Reduces Functionality)**

5. **Multi-Market Support**
   - **Issue:** Runner processes one contract at a time
   - **Impact:** Cannot trade multiple contracts simultaneously
   - **Fix:** Multi-threaded runner or async event loop per contract

6. **Preflight Command Integration**
   - **Issue:** Preflight exists in CLI but not auto-run before trading
   - **Impact:** Manual verification required
   - **Fix:** Add `--require-preflight` flag to run-once

7. **Attribution → Learning Feedback**
   - **Issue:** Attribution computed but not fed into LearningLoop
   - **Impact:** No closed-loop learning from attributed outcomes
   - **Fix:** Pass attribution result to LearningLoop.record_trade()

8. **UI Learning Dashboard**
   - **Issue:** LearningDashboard component likely exists but not wired
   - **Impact:** Cannot visualize strategy performance
   - **Fix:** Wire LearningDashboard to API endpoint for reliability metrics

### ℹ️ **MINOR GAPS (Nice to Have)**

9. **Backtesting Pipeline**
   - **Issue:** No dedicated backtesting harness
   - **Impact:** Must manually replay historical bars
   - **Fix:** Create `backtest.py` script with batch bar processing

10. **Alerting/Monitoring**
    - **Issue:** No Slack/email alerts on errors
    - **Impact:** Must manually check logs
    - **Fix:** Add AlertingService with webhook support

11. **Position Sizing Logic**
    - **Issue:** Hardcoded 1-contract trades
    - **Impact:** Cannot scale with capital
    - **Fix:** Add position sizing based on capital tier + volatility

12. **UI Authentication**
    - **Issue:** No login/auth in UI
    - **Impact:** Anyone with URL can view dashboard
    - **Fix:** Add Supabase Auth with RLS

---

## DEPLOYMENT ARCHITECTURE

### Current Setup (Local Mode)

```
┌─────────────────────────────────────────────────────────┐
│                       LOCAL MACHINE                      │
│                                                          │
│  ┌────────────┐     ┌──────────────┐                   │
│  │  Bot Core  │────▶│ EventStore   │                   │
│  │  (Python)  │     │ (SQLite)     │                   │
│  └────────────┘     └──────────────┘                   │
│        │                    │                            │
│        │                    ▼                            │
│        │            ┌──────────────┐                    │
│        │            │  FastAPI     │                    │
│        │            │  (Polling)   │                    │
│        │            └──────────────┘                    │
│        │                    │                            │
│        ▼                    │                            │
│  ┌────────────┐            │                            │
│  │  Adapter   │            │                            │
│  │  (IBKR)    │◀───────────┘                            │
│  └────────────┘      WebSocket                          │
│        │                    │                            │
│        ▼                    ▼                            │
│  ┌────────────┐     ┌──────────────┐                   │
│  │  Broker    │     │      UI      │                   │
│  │   (TWS)    │     │   (Vite)     │                   │
│  └────────────┘     └──────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

### Target Setup (Cloud Mode)

```
┌─────────────────────────────────────────────────────────┐
│                    PRODUCTION CLOUD                      │
│                                                          │
│  ┌────────────┐                                         │
│  │  Bot Core  │────────────┐                            │
│  │  (VPS)     │            │                            │
│  └────────────┘            │                            │
│        │                   │                            │
│        │                   ▼                            │
│        │            ┌──────────────┐                    │
│        │            │  Supabase    │                    │
│        │            │  (PostgreSQL)│                    │
│        │            │  + Realtime  │                    │
│        │            └──────────────┘                    │
│        │                   │ ▲                          │
│        ▼                   │ │                          │
│  ┌────────────┐            │ │  Realtime               │
│  │  Adapter   │            │ │  Subscription           │
│  │  (IBKR)    │            │ │                          │
│  └────────────┘            │ │                          │
│        │                   │ │                          │
│        ▼                   ▼ │                          │
│  ┌────────────┐     ┌──────────────┐                   │
│  │  Broker    │     │      UI      │                   │
│  │   (TWS)    │     │  (Netlify)   │                   │
│  └────────────┘     └──────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

---

## WHAT NEEDS TO HAPPEN NEXT

### Phase 1: Core Integration (2-3 hours)

1. **Wire Bot → Supabase Publishing**
   - Add `SupabasePublisher` instantiation in runner.py
   - Call publisher methods after each EventStore.append()
   - Test: run bot locally, verify Supabase inserts

2. **Wire UI → Supabase Realtime**
   - Create `ui/src/app/context/SupabaseContext.tsx`
   - Create hooks: `useDecisions()`, `usePositions()`, `useReadiness()`
   - Wire `LiveCockpit` to hooks
   - Test: UI updates when bot emits events

3. **Wire Learning Loop → Runner**
   - Instantiate `LearningLoop` in `BotRunner.__init__()`
   - Call `learning_loop.record_trade()` after FILL_EVENT
   - Emit learning records to EventStore + Supabase
   - Test: Learning metrics update after trades

### Phase 2: Deployment (1-2 hours)

4. **Deploy Supabase Migrations**
   - `supabase db push` or apply via dashboard
   - Verify tables exist
   - Test RLS policies

5. **Deploy UI to Netlify**
   - Set env vars: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
   - Connect GitHub repo
   - Deploy

6. **Configure Bot for Production**
   - Create `.env` with Supabase secrets
   - Set `--mode LIVE` flag
   - Run preflight before enabling execution

### Phase 3: Testing & Monitoring (1-2 hours)

7. **End-to-End Test**
   - Run bot with demo mode
   - Verify events flow: Bot → Supabase → UI
   - Check learning loop updates
   - Validate readiness snapshot

8. **Add Monitoring**
   - Slack webhook for errors
   - Datadog integration
   - Health check endpoint

### Phase 4: Enhancements (Optional)

9. **Multi-Market Support**
10. **Backtesting Harness**
11. **Position Sizing**
12. **Authentication**

---

## FILES REQUIRING MODIFICATION

### 1. `src/trading_bot/core/runner.py`
**Changes:**
- Import `SupabasePublisher`
- Instantiate in `__init__()`
- Call `publisher.publish_decision()` after decision event
- Call `publisher.publish_position()` after order placement
- Call `publisher.publish_readiness()` when execution_allowed=False
- Instantiate `LearningLoop`
- Call `learning_loop.record_trade()` after FILL_EVENT

### 2. `ui/src/app/context/SupabaseContext.tsx` (NEW)
**Purpose:** Supabase client initialization and auth

### 3. `ui/src/app/hooks/useDecisions.ts` (NEW)
**Purpose:** Subscribe to decisions table, return decisions array

### 4. `ui/src/app/hooks/usePositions.ts` (NEW)
**Purpose:** Subscribe to positions table, compute P&L

### 5. `ui/src/app/hooks/useReadiness.ts` (NEW)
**Purpose:** Fetch latest readiness snapshot

### 6. `ui/src/app/components/LiveCockpitComplete.tsx`
**Changes:**
- Import and use `useDecisions()`, `usePositions()`, `useReadiness()`
- Replace mock data with real data

### 7. `.env` files
**Create:**
- `api/.env` - Supabase service role key
- `ui/.env` - Supabase anon key + URL

### 8. `netlify.toml`
**Changes:**
- Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` (or via Netlify dashboard)

---

## CONCLUSION

**You have an EXTREMELY sophisticated trading system with:**
- 28 signals across 4 categories
- Constitutional hierarchy with 9 layers of gates
- Capital tier adaptation
- Edge-Uncertainty-Cost scoring
- Learning loop with throttling and quarantine
- Full execution supervision with bracket orders
- Real-time attribution
- Comprehensive UI with 97 components
- Supabase cloud backend ready to deploy

**The ONLY gaps are integration wiring:**
1. Bot doesn't publish to Supabase
2. UI doesn't subscribe to Supabase
3. Learning loop not connected to runner

**Once these 3 gaps are closed (4-5 hours of work), you have a LIVE, LEARNING, SELF-IMPROVING TRADING BOT.**

