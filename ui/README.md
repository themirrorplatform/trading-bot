# Trading Bot Cockpit (Phase-2 UI)

A read-only web interface for monitoring your trading bot in real-time via Supabase.

## Features

- 🔐 **Passwordless Authentication** via Supabase Auth (magic link)
- 📊 **Real-time Health Monitoring** (DVS, EQS, kill switch status)
- 💰 **Live P&L Tracking** (equity, positions, realized/unrealized P&L)
- 📝 **Event Timeline** (all bot events in real-time)
- ⚡ **Supabase Realtime** subscriptions (live updates)
- 🔒 **Security Hardened** (no secrets, read-only, RLS enforced)

## Technology Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Zustand** - State management
- **Supabase** - Backend (Postgres + Realtime + Auth)
- **Netlify** - Static hosting

## Quick Start

### Prerequisites

- Node.js 18+ installed
- Supabase project set up
- Environment variables configured

### Installation

```bash
cd ui
npm install
```

### Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your Supabase credentials:

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_DEFAULT_DEVICE_ID=bot-01
VITE_APP_MODE=cloud
```

### Development

Start the development server:

```bash
npm run dev
```

Visit `http://localhost:5173`

### Production Build

Build for production:

```bash
npm run build
```

Preview the production build:

```bash
npm run preview
```

## Deployment

See [NETLIFY_SETUP.md](./NETLIFY_SETUP.md) for complete deployment instructions.

### Quick Deploy to Netlify

1. Push repo to GitHub
2. Netlify → Import from Git
3. Configure:
   - Base directory: `ui`
   - Build command: `npm run build`
   - Publish directory: `ui/dist`
4. Set environment variables in Netlify dashboard
5. Deploy!

## Project Structure

```
ui/
├── src/
│   ├── main.tsx              # App entry point
│   ├── App.tsx               # Root component
│   ├── index.css             # Global styles
│   ├── lib/
│   │   ├── supabase.ts       # Supabase client
│   │   └── types.ts          # TypeScript types
│   ├── stores/
│   │   └── botStore.ts       # Zustand store
│   ├── components/
│   │   ├── Auth.tsx          # Authentication
│   │   ├── HealthMonitor.tsx # Health display
│   │   ├── SnapshotView.tsx  # Snapshot display
│   │   └── Timeline.tsx      # Event timeline
│   └── pages/
│       └── Dashboard.tsx     # Main dashboard
├── public/
│   ├── _redirects            # Netlify SPA routing
│   └── _headers              # Security headers
├── package.json
├── vite.config.ts
├── tsconfig.json
└── README.md
```

## Security

### What's Safe

✅ Anon key exposed (public, RLS-protected)
✅ Client-side SELECT queries
✅ Realtime subscriptions
✅ User authentication

### What's NOT Here

❌ Service role key (never in UI)
❌ Bot credentials
❌ Broker API keys
❌ Write operations to bot tables
❌ Direct bot control

**This UI is read-only by design.**

## Supabase Setup Requirements

### Required Tables

```sql
-- Bot events (append-only)
CREATE TABLE bot_events (
  id TEXT PRIMARY KEY,
  device_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Latest snapshot (one row per device)
CREATE TABLE bot_latest_snapshot (
  device_id TEXT PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  equity NUMERIC NOT NULL,
  position INTEGER NOT NULL,
  unrealized_pnl NUMERIC NOT NULL,
  realized_pnl NUMERIC NOT NULL,
  daily_pnl NUMERIC NOT NULL,
  signals JSONB,
  beliefs JSONB,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bot health (one row per device)
CREATE TABLE bot_health (
  device_id TEXT PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL,
  dvs NUMERIC NOT NULL,
  eqs NUMERIC NOT NULL,
  kill_switch_active BOOLEAN NOT NULL,
  last_heartbeat TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Required RLS Policies

```sql
-- Enable RLS
ALTER TABLE bot_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_latest_snapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_health ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read
CREATE POLICY "Authenticated users can read bot_events"
  ON bot_events FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Authenticated users can read bot_latest_snapshot"
  ON bot_latest_snapshot FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Authenticated users can read bot_health"
  ON bot_health FOR SELECT
  TO authenticated
  USING (true);
```

### Enable Realtime

```sql
-- Enable realtime for all three tables
ALTER PUBLICATION supabase_realtime ADD TABLE bot_events;
ALTER PUBLICATION supabase_realtime ADD TABLE bot_latest_snapshot;
ALTER PUBLICATION supabase_realtime ADD TABLE bot_health;
```

## Troubleshooting

### "No events yet"

- Verify bot is running and publishing to Supabase
- Check `device_id` matches `VITE_DEFAULT_DEVICE_ID`
- Verify Realtime is enabled for `bot_events` table

### "No snapshot data available"

- Verify bot has published at least one snapshot
- Check RLS policies allow SELECT
- Verify table exists and has data

### Authentication not working

- Verify `VITE_SUPABASE_URL` is correct
- Verify `VITE_SUPABASE_ANON_KEY` is correct
- Enable Email provider in Supabase Auth settings
- Configure redirect URLs in Supabase dashboard

### Realtime not updating

- Check browser console for subscription errors
- Verify Realtime is enabled in Supabase project settings
- Check RLS policies
- Verify network is not blocking WebSocket connections

## License

Same as parent project.
