# Live Trading Bot: Implementation Roadmap

**Status: Starting Production Build Phase**  
**Date:** December 27, 2025

---

## Current Project State Audit

### ✓ COMPLETED
| Component | Status | Details |
|-----------|--------|---------|
| **Core Bot Logic** | ✓ Complete | 13 modules (signals, decisions, learning, execution, risk) |
| **IBKR Adapter** | ✓ Complete | Hard execution gate, readiness computation, multi-session support |
| **CLI** | ✓ Complete | preflight, status, readiness, run-once commands; --print-json flags |
| **Readiness Module** | ✓ Complete | Shared computation (PDH/PDL/PDC, ONH/ONL, VWAP, ATR, DTE) |
| **Event Store** | ✓ Complete | SQLite schema with DECISION_1M, READINESS_SNAPSHOT, audit trail |
| **UI Components** | ✓ Complete | 17+ components (LiveCockpit, BeliefStatePanel, ExecutionBlame, etc.) |
| **Supabase Schema** | ✓ Complete | 5 migrations (tables, RLS, Realtime, publisher functions, audit) |
| **Netlify Config** | ✓ Complete | build script, environment variables, SPA routing |
| **Git History** | ✓ Complete | 19 commits on main; 10 on origin tracking; bias/learning implementations |
| **Multi-Session Support** | ✓ Complete | RTH (09:30-16:00 ET), Globex (17:00-16:00 ET), pre-market |

### ⚠ PARTIALLY COMPLETE
| Component | Status | Gap | Severity |
|-----------|--------|-----|----------|
| **API Backend** | 0% | No streaming/REST API for UI ↔ Bot | HIGH |
| **Live Data Adapter** | 50% | Has IBKR; missing Binance, forex, Kraken | MEDIUM |
| **Learning Pipeline** | 70% | Has evolution engines; missing data ingestion + feedback loop | MEDIUM |
| **UI Integration** | 30% | Components built; no WebSocket/Supabase wiring | HIGH |
| **Deployment** | 0% | Netlify config exists; no secrets, env setup, CI/CD | HIGH |
| **Multi-Market Support** | 20% | Has ET logic; missing Asia/London session handling | MEDIUM |
| **Monitoring** | 20% | Has event log; missing alerting, Slack webhooks, metrics export | MEDIUM |

### ❌ NOT STARTED
| Component | Impact | Blocker |
|-----------|--------|---------|
| **API → UI Bridge** | HIGH | No real-time decision/position streaming |
| **Supabase Client Integration** | HIGH | UI can't read/write to DB |
| **Secrets Management** | HIGH | Can't deploy without env vars |
| **Bot → API Streaming** | HIGH | Bot produces events; nowhere to send them |
| **Backtesting Pipeline** | MEDIUM | Can't validate learning on historical data |
| **Multi-Currency Support** | MEDIUM | Single USD portfolio only |

---

## Implementation Plan: Phases 1–5

### **PHASE 1: API Backend & Streaming** (Days 1–2)
**Goal:** Bot writes to Supabase; UI reads from Supabase in real-time

#### 1.1 Create Python FastAPI Backend
```
api/
  main.py (FastAPI app with Supabase client)
  models.py (DecisionEvent, PositionUpdate, ReadinessSnapshot)
  supabase_client.py (connection, RLS auth)
  requirements.txt (fastapi, supabase-py, websockets)
```

**What it does:**
- Bot calls `POST /api/decisions` → Supabase inserts + Realtime notify
- Bot calls `POST /api/positions` → Supabase updates + broadcast
- Bot calls `POST /api/readiness` → Supabase stores snapshot
- UI subscribes to Realtime changes (auto-refresh dashboard)

#### 1.2 Instrument Bot to Write Events
- Modify `runner.py`: emit DECISION_1M → API post
- Modify `execution_supervisor.py`: emit trade → API post
- Add error handler: if API fails, log locally, retry on recovery

#### 1.3 Build Supabase Python Client Wrapper
```python
class SupabasePublisher:
    def publish_decision(self, decision_event: dict) → id
    def publish_position(self, position: dict) → id
    def publish_readiness(self, snapshot: dict) → id
    def get_latest_status(self) → dict
```

**Outcome:** Bot ⟷ Supabase wired; events persist; Realtime subscriptions working.

---

### **PHASE 2: UI ↔ Supabase Bridge** (Days 2–3)
**Goal:** Dashboard shows live trading, decisions, positions, P&L

#### 2.1 Create Supabase Client Context
```typescript
// ui/src/app/context/SupabaseContext.tsx
export const useSupabaseClient = () => {
  const client = useMemo(() => createClient(url, key), []);
  useEffect(() => {
    // Subscribe to decisions channel
    const sub = client
      .channel('decisions')
      .on('postgres_changes', {...}, (payload) => {
        updateDecisions(payload.new);
      })
      .subscribe();
    return () => sub.unsubscribe();
  }, []);
  return client;
};
```

#### 2.2 Wire Components to Real Data
```typescript
// LiveCockpit.tsx
const { decisions, positions, readiness } = useSupabaseData();
return (
  <div>
    <PositionPanel data={positions} />
    <DecisionLog data={decisions} />
    <ReadinessGauge data={readiness} />
  </div>
);
```

#### 2.3 Add Missing Components
- **PositionTracker:** Show open trades, P&L, Greeks (if options)
- **PerfChart:** Equity curve, drawdown, daily returns
- **MultiMarketView:** Separate panes for MES, CL, NQ, GC, ES
- **AlertBanner:** Session transitions, margin warnings, execution blocks

**Outcome:** Dashboard fully live with real-time data from bot.

---

### **PHASE 3: Multi-Market Adapters** (Days 3–4)
**Goal:** Bot can trade futures across markets + sessions (US, Asia, London)

#### 3.1 Extend Adapter Pattern
```python
class AdapterFactory:
    def create(self, exchange: str, contract: str) -> Adapter:
        if exchange == 'ibkr':
            return IBKRAdapter(contract)
        elif exchange == 'binance':
            return BinanceAdapter(contract)
        elif exchange == 'crypto':
            return CryptoExchangeAdapter(contract)
```

#### 3.2 Implement Market-Specific Adapters
- **BinanceAdapter:** Crypto futures (BTC, ETH, SOL 24/5)
- **CryptoExchangeAdapter:** Spot + margin (Kraken, Bybit)
- **ForexAdapter:** EUR/USD, GBP/USD (IBKR Forex)
- **ExtendedHoursAdapter:** US pre-market, after-hours, international sessions

#### 3.3 Add Session Manager
```python
class SessionManager:
    def get_active_contracts(self, now_utc: datetime) -> List[Contract]:
        # Return tradeable contracts based on hour
        # 08:00 GMT → London opens
        # 14:30 GMT → Asia overlaps London
        # 17:00 ET → Globex opens
        # 18:00 ET → London closes
        ...
    
    def get_session_info(self, contract: Contract) -> SessionInfo:
        return {
            'session': 'LONDON' | 'ASIA' | 'RTH' | 'GLOBEX',
            'opens_at': datetime,
            'closes_at': datetime,
            'dte': int,
            'liquidity_tier': 'HIGH' | 'MEDIUM' | 'LOW'
        }
```

**Outcome:** Bot can scale across 5+ liquid markets; no manual contract selection.

---

### **PHASE 4: Learning & Evolution Pipeline** (Days 4–5)
**Goal:** Bot learns from trades, updates signal weights, improves over time

#### 4.1 Implement Data Ingestion
```python
class HistoricalDataLoader:
    def load_bars(self, contract: Contract, lookback: int) → BarSeries:
        # Load from Supabase (if cached) or fetch fresh from IBKR
        ...
    
    def load_trades(self, contract: Contract, days: int) → TradeLog:
        # Load from SQLite event store
        ...
    
    def compute_signal_correlations(self, bars, trades) → CorrelationMatrix:
        # See which signals predicted trades
        ...
```

#### 4.2 Wire Learning Loop
```python
class LearningLoop:
    def on_trade_close(self, trade: ClosedTrade):
        # Compute P&L attribution
        # Update belief weights
        # Log learning record to Supabase
        self.evolution_engine.update_weights(trade)
        
    def on_session_close(self):
        # Compute correlation matrix
        # Identify best/worst signals
        # Persist signals for next session
        self.evolution_engine.rebalance_thresholds()
```

#### 4.3 Build Learning Dashboard
```typescript
// ui/src/app/components/LearningDashboard.tsx
export const LearningDashboard = () => {
  const { trades, correlations, weights } = useLearningData();
  return (
    <div>
      <PerformanceBySignal data={correlations} />
      <SignalWeightChart data={weights} />
      <TradeJournal data={trades} />
    </div>
  );
};
```

**Outcome:** Bot evolves in real-time; trades feed learning loop; dashboard shows progress.

---

### **PHASE 5: Deployment & Ops** (Days 5–6)
**Goal:** Bot runs continuously on Netlify + Supabase infrastructure

#### 5.1 Secrets & Environment Setup
```bash
# .env (API)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...
IBKR_ACCOUNT_ID=DU123456
IBKR_API_PORT=7497

# netlify.toml (UI)
[build.environment]
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...

# docker-compose.yml (local API + bot)
services:
  api:
    build: api/
    environment: ${env vars}
    ports: ["8000:8000"]
  bot:
    build: src/trading_bot/
    depends_on: [api]
    environment: ${env vars}
```

#### 5.2 Deploy Backend
```bash
# Option A: Netlify Functions
# Option B: Railway/Heroku with uvicorn
# Option C: GCP Cloud Run (recommended)

# Deploy script:
cd api && pip install -r requirements.txt
gunicorn main:app --workers 2
```

#### 5.3 Netlify Frontend Deployment
```bash
cd ui
npm run build
# Connect GitHub repo to Netlify
# Deploy on every push to main
# Monitor at https://your-bot.netlify.app
```

#### 5.4 Bot as Service
```bash
# systemd service (Linux)
[Unit]
Description=Trading Bot v1
After=network.target

[Service]
Type=simple
User=trading
WorkingDirectory=/opt/trading-bot
ExecStart=/opt/trading-bot/src/trading_bot/.venv/bin/python -m trading_bot.cli run --mode LIVE
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### 5.5 Monitoring & Alerts
```python
class AlertingService:
    def send_slack(self, message: str, channel: str):
        # Post to #trading-alerts
        ...
    
    def on_execution_error(self, error: Exception):
        self.send_slack(f"⚠️ Execution error: {error}", "#alerts")
    
    def on_session_open(self, session: str):
        self.send_slack(f"✓ {session} session open", "#trading-status")
```

**Outcome:** Bot running live on production infrastructure; monitored 24/5; auto-restart on failure.

---

## Detailed Task List

### PHASE 1: API Backend (Days 1–2)

#### Day 1: Setup & Core API
- [ ] Create `api/requirements.txt` (fastapi, uvicorn, supabase-py, pydantic)
- [ ] Create `api/models.py` with DecisionEvent, PositionUpdate, ReadinessSnapshot Pydantic models
- [ ] Create `api/supabase_client.py` with auth and RLS handling
- [ ] Create `api/main.py` with FastAPI app and endpoints:
  - [ ] `POST /api/decisions` → insert to Supabase decisions table
  - [ ] `POST /api/positions` → upsert to Supabase positions table
  - [ ] `POST /api/readiness` → insert to Supabase readiness_snapshots table
  - [ ] `GET /api/status` → return latest bot status
  - [ ] `GET /api/decisions?limit=50` → stream latest decisions
- [ ] Add CORS middleware for UI origin
- [ ] Test API locally: `python -m uvicorn api.main:app --reload`
- [ ] Create `api/Dockerfile` for containerization

**Deliverable:** FastAPI backend running on localhost:8000; Supabase integration tested

#### Day 2: Bot Instrumentation
- [ ] Modify `src/trading_bot/core/runner.py`:
  - [ ] Create `SupabasePublisher` class in runner
  - [ ] Call `publisher.publish_decision(decision)` after DECISION_1M creation
  - [ ] Call `publisher.publish_position(position)` after trade open/close
  - [ ] Call `publisher.publish_readiness(snapshot)` after READINESS_SNAPSHOT emission
- [ ] Modify `src/trading_bot/core/execution_supervisor.py`:
  - [ ] Publish execution errors to `POST /api/errors`
  - [ ] Log "execution_enabled=False" to API when gate closes
- [ ] Create `src/trading_bot/integrations/supabase_publisher.py`:
  - [ ] Async HTTP client to API
  - [ ] Retry logic on failure
  - [ ] Local fallback if API unreachable
- [ ] Test end-to-end: run bot locally, check Supabase inserts

**Deliverable:** Bot writes all events to Supabase; Realtime listeners can subscribe

---

### PHASE 2: UI Integration (Days 2–3)

#### Day 2: Supabase Context & Hooks
- [ ] Create `ui/src/app/context/SupabaseContext.tsx`:
  - [ ] Initialize Supabase client with URL + key from env
  - [ ] Export `useSupabaseClient()` hook
  - [ ] Export `useSupabaseAuth()` for future login
- [ ] Create `ui/src/app/hooks/useDecisions.ts`:
  - [ ] Subscribe to `decisions` channel
  - [ ] Return `decisions[]` + mutation handlers
  - [ ] Auto-refresh on new inserts
- [ ] Create `ui/src/app/hooks/usePositions.ts`:
  - [ ] Subscribe to `positions` channel
  - [ ] Track open/closed trades
  - [ ] Calculate P&L in real-time
- [ ] Create `ui/src/app/hooks/useReadiness.ts`:
  - [ ] Fetch latest readiness snapshot
  - [ ] Expose levels, distances, DTE
- [ ] Test: UI console shows real-time data

#### Day 3: Component Wiring
- [ ] Update `LiveCockpitComplete.tsx`:
  - [ ] Wire to `usePositions()` and show live positions
  - [ ] Wire to `useDecisions()` and show decision log
  - [ ] Add P&L calculation and display
- [ ] Create `PositionTracker.tsx` component:
  - [ ] Show open positions with entry price, current price, P&L %
  - [ ] Show closed trades with closed P&L + days held
  - [ ] Sort by entry time or P&L descending
- [ ] Create `EquityCurve.tsx` component:
  - [ ] Chart using recharts or chart.js
  - [ ] Show daily equity history
  - [ ] Overlay drawdown shading
- [ ] Create `MultiMarketView.tsx` component:
  - [ ] Tabs for MES, CL, NQ, GC, ES
  - [ ] Per-market P&L, position count, status
- [ ] Update `AlertBanner.tsx`:
  - [ ] Show session open/close warnings
  - [ ] Show execution gate status
  - [ ] Color-code: green (ready), yellow (warning), red (blocked)
- [ ] Test: Dashboard auto-updates when bot publishes events

**Deliverable:** UI fully live; dashboard shows positions, P&L, decisions in real-time

---

### PHASE 3: Multi-Market Support (Days 3–4)

#### Day 3: Adapter Expansion
- [ ] Create `src/trading_bot/adapters/binance_adapter.py`:
  - [ ] Connect to Binance futures API
  - [ ] Support BTC, ETH, SOL, XRP perps
  - [ ] Implement `place_order()`, `get_positions()`, `get_account_info()`
- [ ] Create `src/trading_bot/adapters/forex_adapter.py`:
  - [ ] Wrap IBKR forex trading
  - [ ] Support EUR/USD, GBP/USD, JPY/USD
  - [ ] Session hours for forex markets
- [ ] Update `src/trading_bot/core/adapter_factory.py`:
  - [ ] Add binance, forex to factory
  - [ ] Add CLI flags: `--exchange binance|ibkr|forex`
- [ ] Test: Factory creates adapters for each market correctly

#### Day 4: Session & Contract Manager
- [ ] Create `src/trading_bot/core/session_manager.py`:
  - [ ] Define session hours (RT H: 09:30-16:00 ET, Globex: 17:00-16:00 ET, Asia: 18:00 ET - 08:00 ET, London: 08:00-16:30 GMT)
  - [ ] Implement `get_active_contracts(now_utc)` → list of currently tradeable contracts
  - [ ] Implement `get_session_for_contract(contract) → SessionInfo`
- [ ] Create `src/trading_bot/adapters/multi_market_manager.py`:
  - [ ] Manage positions across multiple adapters
  - [ ] Consolidated P&L calculation
  - [ ] Cross-session risk aggregation
- [ ] Add to `runtime.yaml`:
  ```yaml
  sessions:
    - name: RTH
      market: US_EQUITY_INDEX
      opens_at: "09:30 ET"
      closes_at: "16:00 ET"
      contracts: [ES, NQ, GC]
    - name: GLOBEX
      market: US_FUTURES
      opens_at: "17:00 ET"
      closes_at: "16:00 ET next day"
      contracts: [MES, MNQ]
    - name: LONDON
      market: FOREX_INDEX
      opens_at: "08:00 GMT"
      closes_at: "16:30 GMT"
      contracts: [EUR, GBP]
    - name: ASIA
      market: CRYPTO
      opens_at: "18:00 ET prev"
      closes_at: "08:00 ET"
      contracts: [BTC, ETH, SOL]
  ```
- [ ] Update runner to iterate over all active contracts/sessions
- [ ] Test: bot switches contracts seamlessly at session boundaries

**Deliverable:** Bot trades across 5+ markets simultaneously; no manual intervention

---

### PHASE 4: Learning Pipeline (Days 4–5)

#### Day 4: Data Ingestion
- [ ] Create `src/trading_bot/learning/data_loader.py`:
  - [ ] Function `load_bars(contract, days=365) → BarSeries`
  - [ ] Fetch from Supabase (if cached) or IBKR (if fresh)
  - [ ] Store cache in `data/cache/bars_{contract}.parquet`
- [ ] Create `src/trading_bot/learning/trade_analyzer.py`:
  - [ ] Load closed trades from SQLite event store
  - [ ] Compute P&L attribution by signal
  - [ ] Build correlation matrix: signal → outcome
- [ ] Add to learning loop:
  ```python
  class LearningLoop:
      def on_session_close(self):
          bars = self.data_loader.load_bars(self.contract, days=30)
          closed_trades = self.analyzer.get_closed_trades()
          correlation = self.analyzer.compute_signal_correlation(bars, closed_trades)
          self.publish_to_supabase(correlation)
  ```
- [ ] Test: Run learning loop on historical data; verify correlations computed

#### Day 5: Evolution & Feedback
- [ ] Integrate `LearningLoop` into `runner.py`:
  - [ ] Call `learning_loop.on_trade_close(trade)` when trade exits
  - [ ] Call `learning_loop.on_session_close()` at market close
  - [ ] Persist learned weights to `contracts/learned_weights.yaml`
- [ ] Create `src/trading_bot/learning/weight_updater.py`:
  - [ ] Compute new threshold multipliers based on correlation
  - [ ] Example: if signal X had 75% win rate → increase its weight 1.2x
  - [ ] If signal Y had 40% win rate → decrease weight 0.8x
  - [ ] Cap changes at ±30% per update to avoid whiplash
- [ ] Add learning dashboard to UI:
  - [ ] Create `ui/src/app/components/LearningDashboard.tsx`
  - [ ] Show signal correlation heatmap
  - [ ] Show threshold evolution over time
  - [ ] Show top/bottom performing signals
- [ ] Test: Run bot for 1 week; verify weights converge; correlations improve

**Deliverable:** Bot learns from real trades; improves signal weights daily

---

### PHASE 5: Deployment (Days 5–6)

#### Day 5: Infrastructure Setup
- [ ] Create secrets management:
  - [ ] Netlify: set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in Netlify UI
  - [ ] API server: use `.env` file (dev) or env vars (prod)
  - [ ] Bot: load from `runtime.yaml` + env overrides
- [ ] Create `docker-compose.yml` for local dev:
  ```yaml
  version: '3.8'
  services:
    api:
      build: api/
      ports: ["8000:8000"]
      environment:
        SUPABASE_URL: ${SUPABASE_URL}
        SUPABASE_KEY: ${SUPABASE_KEY}
    bot:
      build: src/trading_bot/
      depends_on: [api]
      environment:
        BOT_MODE: DEMO
        API_URL: http://api:8000
  ```
- [ ] Create `api/Dockerfile`:
  ```dockerfile
  FROM python:3.13
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install -r requirements.txt
  COPY . .
  CMD ["gunicorn", "main:app", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker"]
  ```
- [ ] Deploy API to Cloud Run / Railway:
  - [ ] Connect GitHub repo
  - [ ] Set env vars from Supabase secrets
  - [ ] Auto-deploy on push to main

#### Day 6: Frontend & Operations
- [ ] Connect UI repo to Netlify:
  - [ ] Link GitHub repo
  - [ ] Set build command: `npm run build`
  - [ ] Set publish dir: `dist`
  - [ ] Add env vars in Netlify UI
  - [ ] Deploy on every push
- [ ] Create bot systemd service (Linux/Mac):
  ```bash
  sudo tee /etc/systemd/system/trading-bot.service > /dev/null << EOF
  [Unit]
  Description=Trading Bot v1
  After=network.target
  
  [Service]
  Type=simple
  User=trading
  WorkingDirectory=/opt/trading-bot
  ExecStart=/opt/trading-bot/src/trading_bot/.venv/bin/python -m trading_bot.cli run
  Restart=on-failure
  RestartSec=10
  StandardOutput=journal
  StandardError=journal
  
  [Install]
  WantedBy=multi-user.target
  EOF
  
  sudo systemctl enable trading-bot
  sudo systemctl start trading-bot
  ```
- [ ] Create monitoring:
  - [ ] Datadog integration (logs, metrics)
  - [ ] Slack alerts: #trading-alerts channel
  - [ ] PagerDuty for critical errors
- [ ] Create runbook:
  - [ ] How to start/stop bot
  - [ ] How to view logs
  - [ ] How to rollback on error
  - [ ] How to drain positions on emergency

**Deliverable:** Bot running 24/5 on production; dashboard live; alerts working

---

## Git Commit Plan

After each phase, commit:

```bash
# Phase 1
git add api/ src/trading_bot/integrations/
git commit -m "feat(api): FastAPI backend with Supabase streaming

- Add FastAPI app with /decisions, /positions, /readiness endpoints
- Implement Supabase client with RLS auth
- Add SupabasePublisher to bot runner
- Wire all events to Supabase Realtime
- Tested end-to-end: bot → Supabase → dashboard"

# Phase 2
git add ui/src/
git commit -m "feat(ui): Live dashboard with Supabase data

- Add SupabaseContext and useDecisions, usePositions hooks
- Wire LiveCockpit and new components to real-time data
- Add PositionTracker, EquityCurve, MultiMarketView
- Auto-refresh on Realtime events
- Dashboard fully operational with live data"

# Phase 3
git add src/trading_bot/adapters/ src/trading_bot/core/session_manager.py
git commit -m "feat(adapters): Multi-market support (Binance, Forex, multi-session)

- Add BinanceAdapter and ForexAdapter
- Implement SessionManager for contract selection
- Add session hours to runtime.yaml
- Multi-market manager for cross-adapter P&L
- Bot can now trade across 5+ markets simultaneously"

# Phase 4
git add src/trading_bot/learning/
git commit -m "feat(learning): Data-driven signal evolution

- Add DataLoader for historical bar ingestion
- Implement TradeAnalyzer for correlation computation
- Wire LearningLoop to trade close/session close events
- Add weight updater with ±30% caps
- Learning dashboard shows signal performance"

# Phase 5
git add docker-compose.yml netlify.toml .env.example api/Dockerfile
git commit -m "feat(deployment): Production deployment on Netlify + Cloud Run

- Add Docker images for API and bot
- Deploy frontend to Netlify (auto-deploy on push)
- Deploy API to Cloud Run with env secrets
- Add systemd service for local bot operation
- Add monitoring: Slack alerts, Datadog integration
- Create operational runbook"

git push origin main
```

---

## Success Criteria

By end of Phase 5, the bot will be **LIVE and LEARNING**:

1. **Real-time Dashboard:** Open https://your-bot.netlify.app → see live positions, P&L, decisions
2. **Multi-Market:** Bot trades MES, CL, GC, BTC, EUR simultaneously
3. **Learning:** Dashboard shows signal correlation improving daily
4. **Reliable:** 99%+ uptime; auto-restart on failure; Slack alerts for issues
5. **Auditable:** Every decision stamped with market context; all trades logged; learning visible

---

## Timeline Summary

| Phase | Duration | Focus | Outcome |
|-------|----------|-------|---------|
| 1 | 1.5 days | API + Bot Integration | Events flow to Supabase |
| 2 | 1 day | UI Live Data | Dashboard shows real trades |
| 3 | 1 day | Multi-Market | Bot trades 5+ markets |
| 4 | 1 day | Learning Loop | Bot improves daily |
| 5 | 1 day | Deployment | Bot runs 24/5 production |
| **Total** | **5.5 days** | **End-to-End Live Bot** | **Ready to evolve** |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| API crashes; events lost | Local queue in bot; retry on recovery |
| UI disconnects from Realtime | Auto-reconnect with exponential backoff |
| Signal weights diverge rapidly | Cap updates at ±30% per session |
| Margin call on multi-market | Aggregate risk across markets; kill switch if margin < 20% |
| Deployment fails; bot stops | Systemd auto-restart; alert on failure; manual runbook |

---

## Next Steps

1. **Today (Dec 27):** Review roadmap; confirm Phase 1 approach
2. **Tomorrow (Dec 28):** Start Phase 1 (API setup + bot instrumentation)
3. **Dec 29:** Complete Phase 1–2 (API + UI)
4. **Dec 30:** Complete Phase 3–4 (Multi-market + Learning)
5. **Dec 31:** Complete Phase 5 (Deployment)
6. **Jan 1:** Bot running LIVE with first 48 hours of data + learning started

