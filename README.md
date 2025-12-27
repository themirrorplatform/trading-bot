# Trading Bot v2 (MES Survival)

Constraint-based trading system for MES futures with:
- **V2 Signal Engine**: 28 signals (VWAP, ATR, volume, microstructure, session)
- **V3 Signal Engine**: 300 bias signals with strategy detection and orchestration
- **Belief Engines**: Sigmoid likelihoods with constraint-signal matrix (V2) + meta-learning (V3)
- **Decision Engine**: Capital tier gates (S/A/B) + EUC scoring
- **Evolution Engine**: Bounded learning from trades with parameter evolution
- **Templates**: K1 (VWAP MR), K2 (Failed Break), K3 (Sweep), K4 (Momentum)
- **Safety**: Kill switch, bracket-only orders, DVS/EQS gates, TTL cancellation
- **Dashboard**: Next.js + Supabase real-time UI

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   DASHBOARD (web/)                  │
│         Next.js + Tailwind + Recharts               │
│              ↓ Supabase Real-time                   │
├─────────────────────────────────────────────────────┤
│               SUPABASE (PostgreSQL)                 │
│   events | trades | daily_summary | journal         │
├─────────────────────────────────────────────────────┤
│                 PYTHON BACKEND                      │
│  SignalEngineV2 → BeliefEngineV2 → DecisionEngineV2 │
│  SignalEngineV3 → Orchestrator → StrategyDetector   │
│              ↓ TradovateAdapter (SIM/LIVE)          │
└─────────────────────────────────────────────────────┘
```

### Core Components

- **Signals**: `SignalEngine` computes session phase, VWAP (typical price, RTH reset at 09:30 ET), True Range, and ATR(14/30) via Wilder smoothing.
- **Decision**: `DecisionEngine` enforces hierarchy — Kill Switch → Constitution → DVS/EQS → Session → Frequency/Position → Drawdown → Template → Friction.
- **Strategy Template**: `F1_MEAN_REVERSION` requires mid-morning phase, price < VWAP by −0.15%, ATR norm in [0.40%, 0.75%], spread ≤ 2 ticks, DVS/EQS thresholds, and no existing position.
- **Execution**: `TradovateAdapter` (SIM + LIVE modes) with fill modes and reconciliation.
- **Events**: `EventStore` (SQLite) + `SupabaseStore` stores events, decisions, and orders.
- **Evolution**: `EvolutionEngine` learns from trades with bounded parameter updates.
- **Meta-Learning**: `MetaLearner` tracks performance patterns and adapts strategies.

## Quick Start

### 1. Python Backend

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -e .[dev]

# Run tests
python -m pytest -q
```

### 2. Web Dashboard

```bash
cd web
npm install
npm run dev
# Open http://localhost:3000
```

### 3. Environment Variables

Create `.env` in root:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
```

Create `web/.env.local`:
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## CLI Commands

```bash
# Initialize local SQLite database
python -m trading_bot.cli init-db --db data/events.sqlite

# Run single bar (SIM)
python -m trading_bot.cli run-once --bar-json samples/bars.json --db data/events.sqlite --adapter tradovate --fill-mode IMMEDIATE

# Run single bar (LIVE)
python -m trading_bot.cli run-once --bar-json samples/bars.json --db data/events.sqlite --adapter tradovate --live --instrument MES --account-id <ID> --access-token <TOKEN>

# Replay JSON bars through pipeline
python -m trading_bot.cli replay-json --bars samples/bars.json --db data/events.sqlite --stream MES_RTH

# Adapter demo (shows TTL and modification caps)
python -m trading_bot.cli adapter-demo --fill-mode TIMEOUT --limit-price 5600.50

# Generate reconciliation report
python -m trading_bot.cli report
```

## Deployment

### Supabase Setup

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select project or create new
3. Navigate to **SQL Editor**
4. Run each migration file in `supabase/migrations/` in order
5. Enable Realtime for `events` table in **Database > Replication**

### Netlify Deployment

1. Connect GitHub repo to Netlify
2. Build settings (auto-detected from `netlify.toml`):
   - Base directory: `web`
   - Build command: `npm run build`
   - Publish directory: `.next`
3. Set environment variables in Netlify dashboard
4. Deploy!

## Capital Tiers

| Tier | Equity Range | Templates | Max Stop | Max Risk |
|------|--------------|-----------|----------|----------|
| S (Survival) | $0 - $2.5k | K1, K2 | 10 ticks | $12 |
| A (Advancement) | $2.5k - $7.5k | K1, K2, K3 | 14 ticks | $15 |
| B (Breakout) | $7.5k+ | K1, K2, K3, K4 | 18 ticks | $15 |

## EUC Scoring

Every potential trade is scored:
```
Score = Edge - Uncertainty - Cost

Edge = E_R × P_lb (expected return × lower bound probability)
Uncertainty = f(DVS, EQS, belief_stability)
Cost = friction / expected_move
```

Only trades with `Score > 0` are executed.

## Safety Mechanisms

- **Kill Switch**: Triggered on position desync, consecutive losses, daily loss limit
- **Bracket Required**: No naked entries - stop + target mandatory
- **No Market Orders**: Limit entries only per execution contract
- **DVS/EQS Gates**: Block trades when data quality < 0.80 or execution quality < 0.75
- **TTL Cancellation**: Unfilled orders cancelled after 90 seconds
- **Reconciliation**: Per-cycle position verification with auto-flatten on mismatch

## Reproducibility

`BotRunner` derives a deterministic `config_hash` from loaded contracts and signal params to fingerprint outputs across runs.

## Project Structure

```
trading-bot/
├── src/trading_bot/
│   ├── engines/           # V2 + V3 signal/belief/decision/evolution engines
│   ├── adapters/          # Tradovate SIM/LIVE, NinjaTrader bridge, data feed
│   ├── core/              # Runner, live_runner, state store, types
│   ├── log/               # SQLite + Supabase event stores
│   └── contracts/         # YAML configuration
├── web/                   # Next.js dashboard
│   ├── app/               # Pages (dashboard, journal, signals, settings)
│   ├── components/        # React components
│   └── lib/supabase/      # Supabase client
├── supabase/
│   └── migrations/        # PostgreSQL schema
├── tests/                 # Test suite
├── netlify.toml           # Deployment config
└── docs/                  # Specifications
```

## Contracts

See `src/trading_bot/contracts/` for `constitution.yaml`, `session.yaml`, `strategy_templates.yaml`, and `risk_model.yaml`.

## Notes

- Timezone: America/New_York (ET) for all session logic.
- Fail-closed: Missing required signals (VWAP, ATR, spread) block trades with explicit reason codes.
- SIM supports fill_mode: IMMEDIATE, DELAYED, PARTIAL, TIMEOUT.
- LIVE adapter is fail-soft: uses HTTP polling if websocket not available.

## License

MIT
