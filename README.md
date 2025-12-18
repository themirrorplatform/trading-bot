# Trading Bot v2 (MES Survival)

Constraint-based trading system for MES futures with:
- **V2 Signal Engine**: 28 signals (VWAP, ATR, volume, microstructure, session)
- **V2 Belief Engine**: Sigmoid likelihoods with constraint-signal matrix
- **V2 Decision Engine**: Capital tier gates (S/A/B) + EUC scoring
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
│              ↓ TradovateAdapter                     │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Python Backend

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -e .[dev]

# Run tests (99 tests)
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
SUPABASE_URL=https://hhyilmbejidzriljesph.supabase.co
SUPABASE_KEY=your-service-role-key
```

Create `web/.env.local`:
```env
NEXT_PUBLIC_SUPABASE_URL=https://hhyilmbejidzriljesph.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## Deployment

### Supabase Setup

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select project or create new
3. Navigate to **SQL Editor**
4. Run each migration file in `supabase/migrations/` in order:
   - `20241218000001_create_events_table.sql`
   - `20241218000002_create_trades_table.sql`
   - `20241218000003_create_daily_summary_table.sql`
   - `20241218000004_create_decision_journal_table.sql`
   - `20241218000005_create_views_and_functions.sql`
   - `20241218000006_row_level_security.sql`

5. Enable Realtime for `events` table:
   - Go to **Database > Replication**
   - Toggle ON for `events` table

### Netlify Deployment

1. Connect GitHub repo to Netlify
2. Build settings (auto-detected from `netlify.toml`):
   - Base directory: `web`
   - Build command: `npm run build`
   - Publish directory: `.next`

3. Set environment variables in Netlify dashboard:
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://hhyilmbejidzriljesph.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
   ```

4. Deploy!

## CLI Commands

```bash
# Initialize local SQLite database
python -m trading_bot.cli init-db --db data/events.sqlite

# Run single bar
python -m trading_bot.cli run-once --bar-json samples/bars.json --db data/events.sqlite

# Replay JSON bars through pipeline
python -m trading_bot.cli replay-json --bars samples/bars.json --db data/events.sqlite --stream MES_RTH

# Adapter demo (shows TTL and modification caps)
python -m trading_bot.cli adapter-demo --fill-mode TIMEOUT --limit-price 5600.50
```

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

## Project Structure

```
trading-bot/
├── src/trading_bot/
│   ├── engines/           # V1 + V2 signal/belief/decision engines
│   ├── adapters/          # Tradovate SIM/LIVE, NinjaTrader bridge
│   ├── core/              # Runner, state store, types
│   ├── log/               # SQLite + Supabase event stores
│   └── contracts/         # YAML configuration
├── web/                   # Next.js dashboard
│   ├── app/               # Pages (dashboard, journal, signals, settings)
│   ├── components/        # React components
│   └── lib/supabase/      # Supabase client
├── supabase/
│   └── migrations/        # PostgreSQL schema
├── tests/                 # 99 tests
├── netlify.toml           # Deployment config
└── docs/                  # Specifications
```

## License

MIT
