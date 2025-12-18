# Quick Start: Deploy Trading Bot + UI

This guide gets your complete system deployed in ~30 minutes.

## System Overview

```
Trading Bot (Python) → SQLite → Publisher → Supabase Edge Function → Postgres + Realtime
                                                                              ↓
                                                                         Netlify UI
                                                                              ↓
                                                                      Your Browser
```

## What You're Deploying

1. **Supabase Backend** (Database + Realtime + Edge Function)
2. **Netlify UI** (React monitoring dashboard)
3. **Bot Configuration** (Connect bot to cloud)

## Prerequisites

- [ ] Supabase account: https://supabase.com
- [ ] Netlify account: https://app.netlify.com
- [ ] GitHub account (repo already exists)
- [ ] Node.js 18+ installed
- [ ] Supabase CLI: `npm install -g supabase`

## Part 1: Deploy Supabase (10 minutes)

### 1.1 Link to Your Project

```bash
cd /path/to/trading-bot
supabase login
supabase link --project-ref hhyilmbejidzriljesph
```

### 1.2 Push Database Migrations

```bash
supabase db push
```

This creates 3 tables:
- `bot_events` - Event timeline
- `bot_latest_snapshot` - Current state
- `bot_health` - Health monitoring

### 1.3 Deploy Edge Function

```bash
supabase functions deploy bot-ingest
```

### 1.4 Set Secret

```bash
# Generate a strong secret
supabase secrets set DEVICE_SHARED_SECRET=$(openssl rand -hex 32)

# SAVE THIS SECRET - you'll need it for the bot
```

### 1.5 Enable Realtime

Go to: https://supabase.com/dashboard/project/hhyilmbejidzriljesph/database/replication

Check these boxes:
- [ ] bot_events
- [ ] bot_latest_snapshot
- [ ] bot_health

### 1.6 Configure Auth

Go to: https://supabase.com/dashboard/project/hhyilmbejidzriljesph/auth/providers

1. Enable **Email** provider
2. Disable confirmations (for testing)
3. Add redirect URL: `http://localhost:5173/**`

**✅ Supabase is now deployed!**

---

## Part 2: Deploy Netlify UI (10 minutes)

### 2.1 Push Code to GitHub

```bash
git push origin main  # or your branch name
```

### 2.2 Create Netlify Site

1. Go to https://app.netlify.com
2. Click "Add new site" → "Import from Git"
3. Select `themirrorplatform/trading-bot`
4. Configure:
   - Base directory: `ui`
   - Build command: `npm run build`
   - Publish directory: `ui/dist`
5. Click "Deploy"

### 2.3 Add Environment Variables

In Netlify → Site settings → Environment variables, add:

```env
VITE_SUPABASE_URL=https://hhyilmbejidzriljesph.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhoeWlsbWJlamlkenJpbGplc3BoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwMjI0MDIsImV4cCI6MjA4MTU5ODQwMn0.jb59TDah4bPoAFIX9lay9rg_wYpjPkcApEAS2R_2FjI
VITE_DEFAULT_DEVICE_ID=bot-01
VITE_APP_MODE=cloud
```

### 2.4 Redeploy

Click "Trigger deploy" after adding variables.

### 2.5 Update Supabase

Get your Netlify URL: `https://YOUR-SITE.netlify.app`

Add to Supabase Auth → URL Configuration → Redirect URLs:
- `https://YOUR-SITE.netlify.app/**`

**✅ UI is now live!**

---

## Part 3: Connect Bot (10 minutes)

### 3.1 Create Publisher Script

Create `src/trading_bot/publisher.py`:

```python
import httpx
import json
import os
from datetime import datetime
from pathlib import Path

EDGE_FUNCTION_URL = os.getenv(
    "SUPABASE_EDGE_FUNCTION_URL",
    "https://hhyilmbejidzriljesph.supabase.co/functions/v1/bot-ingest"
)
DEVICE_SECRET = os.getenv("DEVICE_SHARED_SECRET")
DEVICE_ID = os.getenv("DEVICE_ID", "bot-01")

def publish_to_supabase(data: dict):
    """Send data to Supabase Edge Function"""
    headers = {
        "Authorization": f"Bearer {DEVICE_SECRET}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "device_id": DEVICE_ID,
        **data
    }
    
    response = httpx.post(
        EDGE_FUNCTION_URL,
        headers=headers,
        json=payload,
        timeout=10.0
    )
    
    if response.status_code == 200:
        print(f"✓ Published to Supabase: {response.json()}")
    else:
        print(f"✗ Failed: {response.status_code} - {response.text}")

# Example: Publish health data
def publish_health():
    data = {
        "health": {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "dvs": 0.95,
            "eqs": 0.90,
            "kill_switch_active": False,
            "last_heartbeat": datetime.utcnow().isoformat()
        }
    }
    publish_to_supabase(data)

if __name__ == "__main__":
    publish_health()
```

### 3.2 Set Environment Variables

```bash
export SUPABASE_EDGE_FUNCTION_URL=https://hhyilmbejidzriljesph.supabase.co/functions/v1/bot-ingest
export DEVICE_SHARED_SECRET=<your-secret-from-step-1.4>
export DEVICE_ID=bot-01
```

### 3.3 Test Publisher

```bash
python src/trading_bot/publisher.py
```

Expected output: `✓ Published to Supabase: {...}`

### 3.4 Integrate with Bot

In your bot's main loop, call `publish_to_supabase()` after each decision:

```python
from trading_bot.publisher import publish_to_supabase

# After making a decision
publish_to_supabase({
    "events": [{
        "id": f"evt_{timestamp}",
        "event_type": "DECISION",
        "timestamp": timestamp.isoformat(),
        "payload": {"action": action, "reason": reason}
    }],
    "snapshot": {
        "timestamp": timestamp.isoformat(),
        "equity": current_equity,
        "position": current_position,
        "unrealized_pnl": unrealized_pnl,
        "realized_pnl": realized_pnl,
        "daily_pnl": daily_pnl
    },
    "health": {
        "timestamp": timestamp.isoformat(),
        "status": "healthy" if dvs > 0.8 else "degraded",
        "dvs": dvs,
        "eqs": eqs,
        "kill_switch_active": kill_switch_active,
        "last_heartbeat": timestamp.isoformat()
    }
})
```

**✅ Bot is now publishing to cloud!**

---

## Verify Everything Works

### 1. Open Netlify UI

Visit your Netlify URL: `https://YOUR-SITE.netlify.app`

### 2. Login

- Enter your email
- Check inbox for magic link
- Click link to login

### 3. Check Dashboard

You should see:
- [ ] Health Monitor (status, DVS, EQS)
- [ ] Snapshot (equity, position, P&L)
- [ ] Timeline (recent events)

### 4. Run Bot

Start your bot. Within seconds, you should see:
- ✅ Health status updates (green = healthy)
- ✅ Snapshot values change in real-time
- ✅ Events appear in timeline

---

## Troubleshooting

### "Unauthorized" from Edge Function

Check: `DEVICE_SHARED_SECRET` matches in bot and Supabase

### UI shows "No data"

1. Check: Bot is running and publishing
2. Check: Edge Function logs: `supabase functions logs bot-ingest`
3. Check: RLS policies allow SELECT for authenticated users

### Realtime not updating

1. Check: Realtime enabled in Supabase dashboard
2. Check: Browser console for WebSocket errors
3. Check: RLS policies are correct

### Can't login

1. Check: Email provider enabled in Supabase Auth
2. Check: Redirect URLs configured
3. Check: Email in spam folder

---

## Next Steps

### Security Hardening

- [ ] Rotate `DEVICE_SHARED_SECRET` monthly
- [ ] Set up Netlify custom domain
- [ ] Enable Supabase WAF rules
- [ ] Configure rate limiting

### Monitoring

- [ ] Set up Netlify notifications
- [ ] Monitor Supabase usage dashboard
- [ ] Set up alerts for DVS/EQS drops

### Scale Up

- [ ] Add multiple bots with different `device_id`
- [ ] Set up database backups
- [ ] Configure auto-scaling

---

## Documentation

- **Netlify Setup**: `/ui/NETLIFY_SETUP.md`
- **Supabase Setup**: `/supabase/README.md`
- **Deployment Checklist**: `/ui/DEPLOYMENT_CHECKLIST.md`
- **Full Architecture**: `/docs/PHASE2_DEPLOYMENT.md`
- **Supabase Steps**: `/supabase/DEPLOYMENT_STEPS.md`

---

## Support

**If stuck:**
1. Check logs: `supabase functions logs bot-ingest --follow`
2. Test Edge Function: `curl` command in `/supabase/README.md`
3. Verify tables exist: Supabase Dashboard → Table Editor
4. Check RLS: Dashboard → Table → "Edit RLS policies"

**Success Criteria:**
✅ Supabase migrations applied
✅ Edge Function responding
✅ Netlify UI deployed
✅ Bot publishing data
✅ Dashboard showing live updates

---

## Time Investment

- ⏱️ Supabase: ~10 minutes
- ⏱️ Netlify: ~10 minutes
- ⏱️ Bot Integration: ~10 minutes
- **Total: ~30 minutes**

## Ongoing Cost

- 💰 Supabase Free Tier: $0/month
- 💰 Netlify Free Tier: $0/month
- **Total: $0/month**

---

**You're now running a production-grade trading bot monitoring system! 🎉**
