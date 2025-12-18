# Supabase Deployment Guide

**Project:** hhyilmbejidzriljesph
**Region:** (auto-detected by Supabase)
**URL:** https://hhyilmbejidzriljesph.supabase.co

## Credentials (Already Configured)

```
Anon Key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhoeWlsbWJlamlkenJpbGplc3BoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwMjI0MDIsImV4cCI6MjA4MTU5ODQwMn0.jb59TDah4bPoAFIX9lay9rg_wYpjPkcApEAS2R_2FjI

Project URL: https://hhyilmbejidzriljesph.supabase.co
```

## Migration Files Ready for Deployment

All 5 migrations are located in `supabase/migrations/`:

| Order | File | Size | Purpose |
|-------|------|------|---------|
| 1 | `20251218_phase2.sql` | 1,677 bytes | Core schema (4 tables + 3 indexes) |
| 2 | `20251218_rls_policies.sql` | 2,207 bytes | Row-Level Security policies |
| 3 | `20251219_realtime_subscriptions.sql` | 844 bytes | Realtime publication enable |
| 4 | `20251219_publisher_functions.sql` | 3,275 bytes | Publisher API functions |
| 5 | `20251219_audit_and_retention.sql` | 1,979 bytes | Audit log + cleanup |

**Total:** 9,982 bytes (~10 KB)

## Step-by-Step Deployment Instructions

### Step 1: Open Supabase SQL Editor

1. Go to: https://app.supabase.com/project/hhyilmbejidzriljesph/sql/new
2. You should be logged in automatically

### Step 2: Deploy Migration 1 (Core Schema)

**File:** `supabase/migrations/20251218_phase2.sql`

- Copy the entire file contents
- Paste into the SQL Editor textarea
- Click the **Execute** button (blue button, bottom right)
- ✅ You should see: "Query returned 0 rows"

**What this creates:**
- `bot_devices` table
- `bot_events` table (with 3 indexes)
- `bot_latest_snapshot` table
- `bot_health` table

### Step 3: Deploy Migration 2 (RLS Policies)

**File:** `supabase/migrations/20251218_rls_policies.sql`

- Copy the entire file contents
- Paste into a NEW SQL query (click + New Query)
- Click **Execute**
- ✅ You should see: "Query returned 0 rows"

**What this creates:**
- Row-Level Security on all tables
- Anon users can read all tables
- Service role can write (via functions only)

### Step 4: Deploy Migration 3 (Realtime Subscriptions)

**File:** `supabase/migrations/20251219_realtime_subscriptions.sql`

- Copy the entire file contents
- Paste into a NEW SQL query
- Click **Execute**
- ✅ You should see: "Query returned 0 rows"

**What this does:**
- Enables Realtime on `bot_events`
- Enables Realtime on `bot_latest_snapshot`
- Enables Realtime on `bot_health`

### Step 5: Deploy Migration 4 (Publisher Functions)

**File:** `supabase/migrations/20251219_publisher_functions.sql`

- Copy the entire file contents
- Paste into a NEW SQL query
- Click **Execute**
- ✅ You should see: "Query returned 0 rows"

**What this creates:**
- `register_bot_device()` function
- `insert_bot_event()` function
- `update_bot_snapshot()` function
- `update_bot_health()` function

### Step 6: Deploy Migration 5 (Audit & Retention)

**File:** `supabase/migrations/20251219_audit_and_retention.sql`

- Copy the entire file contents
- Paste into a NEW SQL query
- Click **Execute**
- ✅ You should see: "Query returned 0 rows"

**What this creates:**
- `bot_audit_log` table
- Audit triggers on inserts/updates
- `cleanup_old_events()` function

## Verification Checklist

After all migrations are deployed, verify in Supabase SQL Editor:

### Test 1: Tables Exist
```sql
SELECT COUNT(*) as table_count FROM pg_tables 
WHERE schemaname = 'public' AND tablename LIKE 'bot_%';
```
**Expected result:** 5 (bot_devices, bot_events, bot_latest_snapshot, bot_health, bot_audit_log)

### Test 2: RLS Enabled
```sql
SELECT tablename, rowsecurity FROM pg_tables 
WHERE schemaname = 'public' AND tablename LIKE 'bot_%';
```
**Expected result:** All should show `t` (true) for rowsecurity

### Test 3: Realtime Active
```sql
SELECT COUNT(*) as realtime_count FROM pg_publication_tables 
WHERE pubname = 'supabase_realtime';
```
**Expected result:** 3 (bot_events, bot_latest_snapshot, bot_health)

### Test 4: Functions Exist
```sql
SELECT proname FROM pg_proc 
WHERE pronamespace = 'public'::regnamespace 
AND (proname LIKE '%bot%' OR proname LIKE 'cleanup%')
ORDER BY proname;
```
**Expected result:** 8 functions (register_bot_device, insert_bot_event, update_bot_snapshot, update_bot_health, log_bot_events_insert, log_bot_health_update, cleanup_old_events, plus others)

### Test 5: Register Test Device
```sql
SELECT register_bot_device('test-device-001', 'Test Device');
```
**Expected result:** true

### Test 6: Verify Test Device
```sql
SELECT * FROM bot_devices WHERE device_id = 'test-device-001';
```
**Expected result:** One row with device_id='test-device-001'

## Environment Configuration

✅ **Already Configured:**
- `ui/.env` created with:
  - `VITE_SUPABASE_URL=https://hhyilmbejidzriljesph.supabase.co`
  - `VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
  - `VITE_DEFAULT_DEVICE_ID=bot-01`
  - `VITE_APP_MODE=cloud`

- `netlify.toml` configured with:
  - Base directory: `ui`
  - Build command: `npm run build`
  - Publish directory: `dist`
  - Redirects for SPA routing

## Next Steps After Migration Deployment

1. ✅ Verify all 5 migrations deployed successfully
2. ✅ Run verification tests (see above)
3. 📋 Go to Netlify (https://app.netlify.com)
4. 📋 Connect GitHub repo to Netlify site
5. 📋 Add environment variables to Netlify:
   - `VITE_SUPABASE_URL=https://hhyilmbejidzriljesph.supabase.co`
   - `VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - `VITE_APP_MODE=cloud`
6. 📋 Netlify auto-deploys when you push to GitHub

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Permission denied" | Make sure you're using service role key in Supabase dashboard |
| "Table already exists" | That's fine! All migrations use `IF NOT EXISTS` |
| "Function not found" | Run migrations 1-4 first, functions are created in migration 4 |
| "Realtime not working" | Check migration 3 was deployed, verify tables in `pg_publication_tables` |

## Support

If you encounter issues:
1. Check Supabase project logs (bottom right of dashboard)
2. Verify each migration file has no syntax errors
3. Ensure migrations are deployed in order (1→2→3→4→5)
4. All migrations are idempotent (safe to re-run if something fails)
