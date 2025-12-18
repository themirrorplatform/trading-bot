# Phase-2 Deployment Guide

## Overview

Phase-2 introduces a **cloud-based monitoring cockpit** for the trading bot. This guide covers the complete deployment architecture.

## Architecture

```
┌─────────────────┐
│   Trading Bot   │ (Local/VPS)
│   (Python)      │
└────────┬────────┘
         │
         │ SQLite event store
         │
         ▼
┌─────────────────┐
│   Publisher     │
│   (Python)      │
└────────┬────────┘
         │
         │ HTTPS
         │
         ▼
┌─────────────────┐
│ Supabase Edge   │
│   Function      │
└────────┬────────┘
         │
         │
         ▼
┌─────────────────┐
│   Supabase      │
│  Postgres +     │
│   Realtime      │
└────────┬────────┘
         │
         │ WebSocket (Realtime)
         │
         ▼
┌─────────────────┐
│  Netlify UI     │
│  (React/Vite)   │
└────────┬────────┘
         │
         │ HTTPS
         │
         ▼
┌─────────────────┐
│   Your Device   │
│ (Phone/Laptop)  │
└─────────────────┘
```

## Components

### 1. Trading Bot (Unchanged)

**Location**: Local machine or VPS
**Function**: 
- Runs trading strategy
- Stores events in SQLite
- No changes required for Phase-2

### 2. Publisher (New)

**Location**: Same as bot
**Function**:
- Reads from SQLite event store
- Publishes to Supabase Edge Function
- Handles authentication with shared secret

### 3. Supabase Edge Function (New)

**Location**: Supabase cloud
**Function**:
- Validates device authentication
- Writes to Postgres tables
- Holds service role key (server-side only)

### 4. Supabase Postgres + Realtime

**Location**: Supabase cloud
**Function**:
- Stores bot_events, bot_latest_snapshot, bot_health
- Broadcasts changes via Realtime
- Enforces RLS policies

### 5. Netlify UI (New)

**Location**: Netlify CDN
**Function**:
- Serves static React app
- Subscribes to Realtime
- Provides authentication (magic link)
- Read-only interface

## Deployment Steps

### Step 1: Set Up Supabase Project

1. **Create Supabase project** at https://supabase.com
2. **Create tables** (see `/ui/README.md` for SQL)
3. **Enable RLS policies** (read-only for authenticated users)
4. **Enable Realtime** for all three tables
5. **Configure Auth**:
   - Enable Email provider
   - Add Netlify domain to allowed redirect URLs
6. **Save credentials**:
   - Project URL: `https://<project-ref>.supabase.co`
   - Anon key: `eyJhbGci...` (public, safe to expose)
   - Service role key: `eyJhbGci...` (private, for Edge Function only)

### Step 2: Deploy Supabase Edge Function

1. **Install Supabase CLI**:
   ```bash
   npm install -g supabase
   ```

2. **Initialize Supabase** (in project root):
   ```bash
   supabase init
   ```

3. **Create Edge Function**:
   ```bash
   supabase functions new bot-ingest
   ```

4. **Implement function** (example):
   ```typescript
   import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
   import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

   serve(async (req) => {
     // Verify shared secret
     const auth = req.headers.get('Authorization')
     if (auth !== `Bearer ${Deno.env.get('DEVICE_SHARED_SECRET')}`) {
       return new Response('Unauthorized', { status: 401 })
     }

     // Parse payload
     const { device_id, events, snapshot, health } = await req.json()

     // Write to Supabase
     const supabase = createClient(
       Deno.env.get('SUPABASE_URL')!,
       Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
     )

     // Insert events, update snapshot/health...
     // (implementation details omitted)

     return new Response('OK', { status: 200 })
   })
   ```

5. **Deploy function**:
   ```bash
   supabase functions deploy bot-ingest
   ```

6. **Set secrets**:
   ```bash
   supabase secrets set DEVICE_SHARED_SECRET=your-secret-here
   ```

### Step 3: Deploy UI to Netlify

1. **Push repo to GitHub** (if not already)

2. **Create Netlify site**:
   - Go to https://app.netlify.com
   - Click "Add new site" → "Import from Git"
   - Select your GitHub repo
   - Configure:
     - Base directory: `ui`
     - Build command: `npm run build`
     - Publish directory: `ui/dist`

3. **Set environment variables** in Netlify:
   ```
   VITE_SUPABASE_URL=https://<project-ref>.supabase.co
   VITE_SUPABASE_ANON_KEY=eyJhbGci...
   VITE_DEFAULT_DEVICE_ID=bot-01
   VITE_APP_MODE=cloud
   ```

4. **Deploy**:
   - Click "Deploy site"
   - Wait for build to complete
   - Site will be live at `https://<random>.netlify.app`

5. **Configure custom domain** (optional):
   - Netlify → Domain settings
   - Add your custom domain
   - Update DNS records

6. **Update Supabase**:
   - Add Netlify URL to Supabase Auth redirect URLs
   - Format: `https://<site>.netlify.app/**`

### Step 4: Configure Publisher

1. **Install dependencies** (if not in bot venv):
   ```bash
   pip install httpx
   ```

2. **Configure environment**:
   ```bash
   export SUPABASE_EDGE_FUNCTION_URL=https://<project-ref>.supabase.co/functions/v1/bot-ingest
   export DEVICE_SHARED_SECRET=your-secret-here
   export DEVICE_ID=bot-01
   ```

3. **Run publisher** (alongside bot):
   ```bash
   python -m trading_bot.publisher
   ```

### Step 5: Verify End-to-End

1. **Start bot** (publishes to SQLite)
2. **Start publisher** (reads SQLite, sends to Supabase)
3. **Open Netlify UI** in browser
4. **Authenticate** with magic link
5. **Verify**:
   - ✅ Health monitor shows bot status
   - ✅ Snapshot updates with P&L
   - ✅ Timeline receives events in real-time
   - ✅ Refreshing page doesn't break

## Security Checklist

### ✅ Safe

- Anon key in Netlify environment (public, RLS-protected)
- JWT authentication for users
- Read-only UI operations
- RLS enforced on all tables

### ❌ Dangerous (Never Do)

- Service role key in UI or Netlify
- Bypass RLS "temporarily"
- Write operations from UI
- Shared secrets in browser
- Broker credentials anywhere near UI

## Monitoring

### Check Bot Health

```sql
SELECT * FROM bot_health WHERE device_id = 'bot-01';
```

### Check Latest Snapshot

```sql
SELECT * FROM bot_latest_snapshot WHERE device_id = 'bot-01';
```

### Check Recent Events

```sql
SELECT * FROM bot_events 
WHERE device_id = 'bot-01' 
ORDER BY timestamp DESC 
LIMIT 10;
```

## Troubleshooting

### UI shows "No events"

1. Check bot is running
2. Check publisher is running
3. Verify Edge Function is receiving data
4. Check RLS policies allow SELECT
5. Verify Realtime is enabled

### "Unauthorized" from Edge Function

1. Check `DEVICE_SHARED_SECRET` matches on both sides
2. Verify `Authorization` header format: `Bearer <secret>`

### UI not loading

1. Check Netlify deploy logs
2. Verify environment variables are set
3. Check browser console for errors

### Realtime not updating

1. Check Supabase Realtime is enabled
2. Verify RLS policies
3. Check browser WebSocket connection
4. Verify device_id filter matches

## Cost Estimates

### Supabase (Free Tier)

- 500MB database
- 2GB bandwidth
- Unlimited API requests
- **Cost**: $0/month

### Netlify (Free Tier)

- 100GB bandwidth
- 300 build minutes
- Unlimited sites
- **Cost**: $0/month

### Total for Phase-2

**$0/month** (within free tiers)

## Scaling Considerations

### When to Upgrade Supabase

- Database > 500MB (unlikely for event data)
- Realtime connections > 200 concurrent
- Need dedicated resources

### When to Upgrade Netlify

- Bandwidth > 100GB/month
- Need advanced features (analytics, etc.)

## Next Phase: Local Dev Mode

Future enhancement to support:

- **Cloud mode**: Supabase Realtime (current)
- **Local mode**: FastAPI + WebSocket (for debugging)

Environment variable switch:
```env
VITE_APP_MODE=local  # or cloud
VITE_LOCAL_WS_URL=ws://localhost:8000/ws
```

This requires no changes to current deployment.

## Support

For issues:
1. Check troubleshooting section above
2. Review Netlify deploy logs
3. Check Supabase logs in dashboard
4. Verify all environment variables

## References

- [UI README](/ui/README.md)
- [Netlify Setup Guide](/ui/NETLIFY_SETUP.md)
- [Supabase Docs](https://supabase.com/docs)
- [Netlify Docs](https://docs.netlify.com)
