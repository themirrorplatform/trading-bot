# Supabase Deployment Steps

Follow these steps **in order** to deploy your Supabase configuration.

## Prerequisites

- [ ] Supabase account created at https://supabase.com
- [ ] Supabase CLI installed: `npm install -g supabase`
- [ ] Git repository cloned locally

## Step 1: Login to Supabase CLI

```bash
supabase login
```

This will open a browser for authentication.

## Step 2: Link to Your Project

```bash
cd /path/to/trading-bot
supabase link --project-ref hhyilmbejidzriljesph
```

Enter your database password when prompted.

## Step 3: Push Database Migrations

```bash
supabase db push
```

This will apply all three migrations:
1. Create bot tables
2. Enable RLS policies
3. Enable Realtime

**Verify**: Check Supabase Dashboard → Table Editor to confirm tables exist.

## Step 4: Generate Device Shared Secret

```bash
# On Windows (PowerShell)
$secret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
echo $secret

# On Mac/Linux
openssl rand -hex 32
```

**Save this secret** - you'll need it for both the Edge Function AND the bot publisher.

## Step 5: Deploy Edge Function

```bash
supabase functions deploy bot-ingest
```

## Step 6: Set Edge Function Secret

Replace `YOUR_SECRET_FROM_STEP_4` with the secret you generated:

```bash
supabase secrets set DEVICE_SHARED_SECRET=YOUR_SECRET_FROM_STEP_4
```

## Step 7: Verify Edge Function

Test the endpoint:

```bash
# Windows (PowerShell)
$headers = @{
    "Authorization" = "Bearer YOUR_SECRET_FROM_STEP_4"
    "Content-Type" = "application/json"
}
$body = @{
    device_id = "bot-01"
    health = @{
        timestamp = (Get-Date).ToUniversalTime().ToString("o")
        status = "healthy"
        dvs = 0.95
        eqs = 0.90
        kill_switch_active = $false
        last_heartbeat = (Get-Date).ToUniversalTime().ToString("o")
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://hhyilmbejidzriljesph.supabase.co/functions/v1/bot-ingest" -Method Post -Headers $headers -Body $body
```

Expected response: `{"success":true,"results":{"health_updated":true}}`

## Step 8: Enable Realtime in Dashboard

Go to: https://supabase.com/dashboard/project/hhyilmbejidzriljesph/database/replication

Verify these tables are checked:
- [ ] `bot_events`
- [ ] `bot_latest_snapshot`
- [ ] `bot_health`

If not, click each table and enable Realtime.

## Step 9: Configure Auth

Go to: https://supabase.com/dashboard/project/hhyilmbejidzriljesph/auth/providers

1. Enable **Email** provider
2. Disable email confirmations (for testing)
3. Add Site URL: `http://localhost:5173`
4. Add Redirect URLs:
   - `http://localhost:5173/**`
   - Your Netlify URL (once deployed)

## Step 10: Update UI Environment

In your local repo, create `/ui/.env`:

```env
VITE_SUPABASE_URL=https://hhyilmbejidzriljesph.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhoeWlsbWJlamlkenJpbGplc3BoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwMjI0MDIsImV4cCI6MjA4MTU5ODQwMn0.jb59TDah4bPoAFIX9lay9rg_wYpjPkcApEAS2R_2FjI
VITE_DEFAULT_DEVICE_ID=bot-01
VITE_APP_MODE=cloud
```

## Step 11: Test UI Locally

```bash
cd ui
npm install
npm run dev
```

Open http://localhost:5173 and verify:
- [ ] Login page loads
- [ ] Can request magic link
- [ ] After login, dashboard shows (no data yet)

## Step 12: Deploy to Netlify

1. Go to https://app.netlify.com
2. Click "Add new site" → "Import from Git"
3. Select your GitHub repository
4. Configure:
   - **Base directory**: `ui`
   - **Build command**: `npm run build`
   - **Publish directory**: `ui/dist`
5. Add environment variables (same as Step 10)
6. Deploy!

## Step 13: Update Supabase Redirect URLs

After Netlify deploy, get your URL: `https://YOUR-SITE.netlify.app`

Add to Supabase Auth redirect URLs:
- `https://YOUR-SITE.netlify.app/**`

## Step 14: Configure Bot Publisher

In your bot's environment, set:

```env
SUPABASE_EDGE_FUNCTION_URL=https://hhyilmbejidzriljesph.supabase.co/functions/v1/bot-ingest
DEVICE_SHARED_SECRET=YOUR_SECRET_FROM_STEP_4
DEVICE_ID=bot-01
```

## Step 15: End-to-End Test

1. Start bot (it will publish to Edge Function)
2. Open Netlify UI
3. Login with email
4. Verify dashboard shows:
   - [ ] Health status (green = healthy)
   - [ ] Snapshot with equity/position
   - [ ] Timeline with events

## Troubleshooting

### Migration fails

```bash
# Check current migration status
supabase db diff

# If needed, reset and retry
supabase db reset
supabase db push
```

### Edge Function deployment fails

```bash
# Check function logs
supabase functions logs bot-ingest --follow

# Redeploy
supabase functions deploy bot-ingest --no-verify-jwt
```

### RLS blocking queries

Go to: Dashboard → Table Editor → Click table → "Edit RLS policies"

Verify policies match migration 002.

### Realtime not working

1. Check: Dashboard → Database → Replication
2. Ensure tables are enabled
3. Check browser console for errors
4. Verify WebSocket connection in Network tab

### UI not loading data

1. Check: Environment variables are set in Netlify
2. Check: Edge Function is deployed and responding
3. Check: Bot is publishing data
4. Check: RLS policies allow SELECT for authenticated users

## Success Criteria

✅ All migrations applied
✅ Edge Function deployed and responding
✅ Realtime enabled on all tables
✅ UI deployed to Netlify
✅ UI can authenticate users
✅ Dashboard shows live bot data

## Next: Configure Bot Publisher

See `/docs/PHASE2_DEPLOYMENT.md` for bot publisher setup.
