# Supabase Setup for Trading Bot

This directory contains all Supabase configuration, migrations, and Edge Functions for the trading bot monitoring system.

## Project Configuration

**Project ID**: `hhyilmbejidzriljesph`  
**Project URL**: `https://hhyilmbejidzriljesph.supabase.co`

## Directory Structure

```
supabase/
├── config.toml                          # Supabase local dev configuration
├── migrations/                          # Database migrations
│   ├── 20241218000001_create_bot_tables.sql
│   ├── 20241218000002_enable_rls.sql
│   └── 20241218000003_enable_realtime.sql
├── functions/                           # Edge Functions
│   └── bot-ingest/
│       └── index.ts                     # Bot data ingestion endpoint
└── README.md                            # This file
```

## Setup Instructions

### 1. Install Supabase CLI

```bash
npm install -g supabase
```

### 2. Login to Supabase

```bash
supabase login
```

### 3. Link to Your Project

```bash
supabase link --project-ref hhyilmbejidzriljesph
```

### 4. Push Migrations to Supabase

```bash
supabase db push
```

This will create:
- `bot_events` table with indexes
- `bot_latest_snapshot` table
- `bot_health` table
- RLS policies for all tables
- Realtime publication for all tables

### 5. Deploy Edge Function

```bash
supabase functions deploy bot-ingest
```

### 6. Set Edge Function Secrets

```bash
supabase secrets set DEVICE_SHARED_SECRET=your-secret-here
```

**Important**: Generate a strong secret for `DEVICE_SHARED_SECRET`. This authenticates the bot publisher to the Edge Function.

Example:
```bash
supabase secrets set DEVICE_SHARED_SECRET=$(openssl rand -hex 32)
```

## Database Tables

### bot_events

Append-only event log for all bot activity.

```sql
CREATE TABLE bot_events (
  id TEXT PRIMARY KEY,
  device_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### bot_latest_snapshot

Current state snapshot (one row per device).

```sql
CREATE TABLE bot_latest_snapshot (
  device_id TEXT PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  equity NUMERIC NOT NULL,
  position INTEGER NOT NULL DEFAULT 0,
  unrealized_pnl NUMERIC NOT NULL DEFAULT 0,
  realized_pnl NUMERIC NOT NULL DEFAULT 0,
  daily_pnl NUMERIC NOT NULL DEFAULT 0,
  signals JSONB,
  beliefs JSONB,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### bot_health

Health monitoring data (one row per device).

```sql
CREATE TABLE bot_health (
  device_id TEXT PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('healthy', 'degraded', 'down')),
  dvs NUMERIC NOT NULL CHECK (dvs >= 0 AND dvs <= 1),
  eqs NUMERIC NOT NULL CHECK (eqs >= 0 AND eqs <= 1),
  kill_switch_active BOOLEAN NOT NULL DEFAULT FALSE,
  last_heartbeat TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## RLS Policies

All tables have Row Level Security enabled:

- **Authenticated users** (UI via anon key + JWT): `SELECT` only
- **Service role** (Edge Function): `ALL` operations

This ensures the UI is read-only while the Edge Function can write data.

## Realtime

All three tables are enabled for Realtime:

- `bot_events`: UI subscribes to `INSERT` events
- `bot_latest_snapshot`: UI subscribes to `UPDATE` events
- `bot_health`: UI subscribes to `UPDATE` events

## Edge Function: bot-ingest

Receives data from the bot publisher and writes to Postgres.

**Endpoint**: `https://hhyilmbejidzriljesph.supabase.co/functions/v1/bot-ingest`

**Authentication**: Bearer token with `DEVICE_SHARED_SECRET`

**Request Format**:

```json
{
  "device_id": "bot-01",
  "events": [
    {
      "id": "evt_123",
      "event_type": "DECISION",
      "timestamp": "2024-12-18T10:30:00Z",
      "payload": { "action": "NO_TRADE", "reason": "DVS_LOW" }
    }
  ],
  "snapshot": {
    "timestamp": "2024-12-18T10:30:00Z",
    "equity": 5000.00,
    "position": 0,
    "unrealized_pnl": 0,
    "realized_pnl": 150.00,
    "daily_pnl": 150.00,
    "signals": {},
    "beliefs": {}
  },
  "health": {
    "timestamp": "2024-12-18T10:30:00Z",
    "status": "healthy",
    "dvs": 0.95,
    "eqs": 0.90,
    "kill_switch_active": false,
    "last_heartbeat": "2024-12-18T10:30:00Z"
  }
}
```

## Local Development

### Start Supabase Locally

```bash
supabase start
```

This starts:
- PostgreSQL on `localhost:54322`
- API Gateway on `localhost:54321`
- Studio UI on `localhost:54323`

### Stop Supabase

```bash
supabase stop
```

### Reset Database

```bash
supabase db reset
```

## Verification

### Check Migrations

```bash
supabase db diff
```

### Check Functions

```bash
supabase functions list
```

### View Logs

```bash
supabase functions logs bot-ingest
```

### Test Edge Function

```bash
curl -X POST \
  https://hhyilmbejidzriljesph.supabase.co/functions/v1/bot-ingest \
  -H "Authorization: Bearer YOUR_DEVICE_SHARED_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "bot-01",
    "health": {
      "timestamp": "2024-12-18T10:30:00Z",
      "status": "healthy",
      "dvs": 0.95,
      "eqs": 0.90,
      "kill_switch_active": false,
      "last_heartbeat": "2024-12-18T10:30:00Z"
    }
  }'
```

## Security

- ❌ **NEVER** commit `DEVICE_SHARED_SECRET` to git
- ❌ **NEVER** expose service role key in UI
- ✅ Edge Function validates device authentication
- ✅ RLS enforces read-only access for UI
- ✅ Service role key stays server-side only

## Next Steps

After running migrations:

1. Update `/ui/.env` with your Supabase credentials
2. Deploy Edge Function and set secrets
3. Configure bot publisher to send data to Edge Function
4. Deploy UI to Netlify
5. Test end-to-end flow

## Support

See:
- [Supabase CLI Docs](https://supabase.com/docs/guides/cli)
- [Edge Functions Docs](https://supabase.com/docs/guides/functions)
- [Realtime Docs](https://supabase.com/docs/guides/realtime)
