# Netlify Setup — Canonical Configuration

## Overview

This document provides the **production-safe way to set up Netlify** for the Phase-2 trading bot cockpit.

### What Netlify is and is not

**Netlify is ONLY the UI host.**

It:
- serves static assets
- runs client-side Supabase queries
- subscribes to Realtime

It does **not**:
- run the bot
- write to Supabase tables
- hold service role keys
- talk directly to the bot

This keeps the system safe.

---

## Repository Structure

The repository is structured as follows:

```
/ui/                          # Frontend application (Netlify)
  package.json
  vite.config.ts
  index.html
  src/
    main.tsx
    App.tsx
    lib/supabase.ts           # Supabase client
    stores/
      botStore.ts             # Zustand state management
    components/
      Auth.tsx                # Authentication component
      HealthMonitor.tsx       # Bot health display
      SnapshotView.tsx        # Current snapshot display
      Timeline.tsx            # Event timeline
    pages/
      Dashboard.tsx           # Main dashboard
  public/
    _redirects              # SPA routing
    _headers                # Security headers
/src/                         # Python bot (runs separately)
/supabase/                    # Supabase migrations (future)
```

---

## 1) Create the Netlify Site

### Option A (recommended): Git-based (automatic deploys)

1. Push repo to GitHub
2. Netlify → **Add new site → Import from Git**
3. Select repo: `themirrorplatform/trading-bot`
4. Configure build settings:

   **Base directory**
   ```
   ui
   ```

   **Build command**
   ```
   npm run build
   ```

   **Publish directory**
   ```
   ui/dist
   ```

5. Click **Deploy site**

### Option B: Manual (only if you must)

```bash
cd ui
npm install
npm run build
```

Then drag `/ui/dist` into Netlify Drop.

⚠️ **Note**: You lose CI/CD with this approach — not recommended.

---

## 2) Environment Variables

### Required Variables

Go to: Netlify → Site settings → **Environment variables**

Add **only these**:

```env
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOi...
VITE_DEFAULT_DEVICE_ID=bot-01
VITE_APP_MODE=cloud
```

### Important Rules

* ❌ NEVER add `SERVICE_ROLE_KEY`
* ❌ NEVER add `DEVICE_SHARED_SECRET`
* ❌ NEVER add broker keys
* ❌ NEVER add bot credentials

**If it feels "useful" to add — it probably doesn't belong here.**

---

## 3) Supabase Client Setup

The Supabase client is configured in `/ui/src/lib/supabase.ts`:

```typescript
import { createClient } from '@supabase/supabase-js';

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL!,
  import.meta.env.VITE_SUPABASE_ANON_KEY!,
  {
    realtime: {
      params: {
        eventsPerSecond: 10,
      },
    },
  }
);
```

This client:
- authenticates users
- subscribes to Realtime
- respects RLS automatically

---

## 4) Authentication Strategy

### Using Supabase Auth (email magic link)

**Why:**
- works instantly
- no password handling
- mobile friendly
- integrates cleanly with RLS

**Flow:**
1. User enters email
2. Supabase sends magic link
3. User clicks link
4. Supabase issues JWT
5. JWT authorizes:
   - SELECT bot_events
   - SELECT bot_latest_snapshot
   - SELECT bot_health

The UI blocks everything until auth resolves.

---

## 5) Realtime Subscriptions

### Timeline Subscription (bot_events)

```typescript
supabase
  .channel('bot-events')
  .on(
    'postgres_changes',
    {
      event: 'INSERT',
      schema: 'public',
      table: 'bot_events',
      filter: `device_id=eq.${deviceId}`,
    },
    (payload) => {
      addEvent(payload.new);
    }
  )
  .subscribe();
```

### Snapshot Subscription (bot_latest_snapshot)

```typescript
supabase
  .channel('bot-snapshot')
  .on(
    'postgres_changes',
    {
      event: '*',
      schema: 'public',
      table: 'bot_latest_snapshot',
      filter: `device_id=eq.${deviceId}`,
    },
    (payload) => setSnapshot(payload.new)
  )
  .subscribe();
```

### Health Subscription (bot_health)

```typescript
supabase
  .channel('bot-health')
  .on(
    'postgres_changes',
    {
      event: '*',
      schema: 'public',
      table: 'bot_health',
      filter: `device_id=eq.${deviceId}`,
    },
    (payload) => setHealth(payload.new)
  )
  .subscribe();
```

---

## 6) Netlify Configuration Files

### `/ui/public/_redirects`

```
/*    /index.html   200
```

This prevents 404s on refresh for SPA routing.

### `/ui/public/_headers`

```
/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer
  Permissions-Policy: camera=(), microphone=(), geolocation=()
```

Security headers to harden the deployment.

### `/netlify.toml` (root)

```toml
[build]
  base = "ui"
  command = "npm run build"
  publish = "ui/dist"

[build.environment]
  NODE_VERSION = "18"
```

---

## 7) Build Hardening

### `vite.config.ts`

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    sourcemap: false,
    target: 'es2020',
  },
});
```

This disables source maps for production builds.

---

## 8) Local Development

### Setup

```bash
cd ui
npm install
cp .env.example .env
```

Edit `.env` with your Supabase credentials.

### Run Development Server

```bash
npm run dev
```

Visit `http://localhost:5173`

### Build for Production

```bash
npm run build
npm run preview
```

---

## 9) Netlify Deploy Verification Checklist

After deploy, confirm:

* ✅ Site loads without console errors
* ✅ Login works (magic link email received)
* ✅ `bot_health` updates live
* ✅ `bot_latest_snapshot` updates
* ✅ Timeline receives new events
* ✅ Refreshing page does not break routing
* ✅ No secrets visible in browser dev tools

---

## 10) System Architecture

```
Bot (local / VPS)
 └─ SQLite event store
 └─ Publisher
     └─ Supabase Edge Function
         └─ Supabase Postgres + Realtime
             └─ Netlify UI (read-only)
                 └─ Your phone / laptop
```

**No coupling. No risk. No silent failure modes.**

---

## 11) What NOT to Do (Common Mistakes)

* ❌ Do NOT expose Edge Function directly to Netlify UI
* ❌ Do NOT allow UI to INSERT bot_events
* ❌ Do NOT bypass RLS "just for now"
* ❌ Do NOT co-host UI + bot on Netlify
* ❌ Do NOT commit `.env` files with real credentials
* ❌ Do NOT add service role keys to Netlify environment

---

## 12) Troubleshooting

### UI Not Loading

1. Check Netlify deploy logs
2. Verify environment variables are set
3. Check browser console for errors

### Auth Not Working

1. Verify `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are correct
2. Check Supabase Auth settings (enable Email provider)
3. Configure allowed redirect URLs in Supabase

### Realtime Not Updating

1. Verify Realtime is enabled in Supabase
2. Check RLS policies allow SELECT for authenticated users
3. Verify `device_id` filter matches your bot's device ID
4. Check browser console for subscription errors

---

## 13) Next Steps

When you're ready for **local dev mode toggle**, this UI can connect to:

* FastAPI + WebSocket (local debugging)
* Supabase Realtime (cloud mode)

The infrastructure is ready for this enhancement when needed.
