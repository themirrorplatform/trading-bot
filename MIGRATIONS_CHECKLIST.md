# Supabase Migrations Deployment Checklist

##  Migrations Created & Committed

All 5 production-ready migrations have been created and pushed to git:

### Migration Files

| # | File | Lines | Purpose | Status |
|----|------|-------|---------|--------|
| 1 | \20251218_phase2.sql\ | 50 | Core schema (4 tables, 3 indexes) |  Ready |
| 2 | \20251218_rls_policies.sql\ | 80 | RLS policies (read: anon, write: service) |  Ready |
| 3 | \20251219_realtime_subscriptions.sql\ | 20 | Enable Realtime on 3 tables |  Ready |
| 4 | \20251219_publisher_functions.sql\ | 100+ | 4 PL/pgSQL functions for publisher writes |  Ready |
| 5 | \20251219_audit_and_retention.sql\ | 80+ | Audit log + triggers + cleanup functions |  Ready |

**Location:** \supabase/migrations/\

---

##  Next Steps to Deploy

### Step 1: Access Your Supabase Project
- Go to https://app.supabase.com
- Select your trading-bot project
- Navigate to **Database  SQL Editor**

### Step 2: Deploy Migrations in Order

**Run each migration in this exact order:**

#### Migration 1 (Core Schema - 2 min)
- Copy all contents from: \supabase/migrations/20251218_phase2.sql\
- Paste into SQL Editor
- Click **"Execute"**
-  Should see: "Query returned 0 rows"

#### Migration 2 (RLS Policies - 2 min)
- Copy all contents from: \supabase/migrations/20251218_rls_policies.sql\
- Paste into SQL Editor
- Click **"Execute"**
-  Should see: "Query returned 0 rows"

#### Migration 3 (Realtime - 1 min)
- Copy all contents from: \supabase/migrations/20251219_realtime_subscriptions.sql\
- Paste into SQL Editor
- Click **"Execute"**
-  Should see: "Query returned 0 rows"

#### Migration 4 (Publisher Functions - 2 min)
- Copy all contents from: \supabase/migrations/20251219_publisher_functions.sql\
- Paste into SQL Editor
- Click **"Execute"**
-  Should see: "Query returned 0 rows"

#### Migration 5 (Audit & Retention - 2 min)
- Copy all contents from: \supabase/migrations/20251219_audit_and_retention.sql\
- Paste into SQL Editor
- Click **"Execute"**
-  Should see: "Query returned 0 rows"

**Total time:** ~10 minutes

---

##  Verification (Run in SQL Editor)

`sql
-- 1. Verify tables exist (should return 4)
SELECT COUNT(*) FROM pg_tables 
WHERE schemaname = 'public' AND tablename LIKE 'bot_%';

-- 2. Verify RLS is enabled on all tables
SELECT tablename, rowsecurity FROM pg_tables 
WHERE tablename LIKE 'bot_%' AND schemaname = 'public';

-- 3. Verify Realtime is enabled (should return 3)
SELECT COUNT(*) FROM pg_publication_tables 
WHERE pubname = 'supabase_realtime';

-- 4. Verify functions exist (should return 4)
SELECT proname FROM pg_proc 
WHERE proname LIKE 'register_bot%' OR proname LIKE 'insert_bot%' 
   OR proname LIKE 'update_bot%' OR proname LIKE 'cleanup%';

-- 5. Verify triggers exist (should return 2)
SELECT trigger_name FROM information_schema.triggers 
WHERE event_object_schema = 'public' AND trigger_name LIKE '%bot%';

-- 6. Test: Register a device
SELECT register_bot_device('verify-bot', 'Verification Device');

-- 7. Verify test device
SELECT * FROM bot_devices WHERE device_id = 'verify-bot';
`

---

##  Get Your API Keys

After migrations are deployed:

1. **Open Project Settings**  **API**

2. **Find these values:**
   - **Project URL** (copy this)
     - Example: \https://abcdefgh.supabase.co\
   - **anon public** key (copy this)
     - Example: \eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\
   - **Service Role Secret** ( KEEP SAFE - for publisher only)
     - Example: \eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\

3. **Store safely:**
   - Project URL  \ui/.env\ as \VITE_SUPABASE_URL\
   - Anon Key  \ui/.env\ as \VITE_SUPABASE_ANON_KEY\
   - Service Key  Keep in Netlify secrets or env file (NEVER commit)

---

##  Schema Overview

### Tables Created

**bot_devices** - Device registry
- \device_id\ (PRIMARY KEY)
- \
ame\ - Human-readable name
- \created_at\ - When registered
- \last_seen_at\ - Heartbeat timestamp

**bot_events** - Event stream (append-only)
- \device_id\, \seq\ (PRIMARY KEY)
- \event_id\ - Unique event ID
- \	s\ - Event timestamp
- \	ype\ - SIGNAL, DECISION, EXECUTION, BLAME, etc.
- \severity\ - INFO, WARN, ERROR, CRITICAL
- \symbol\ - Trading pair
- \session\ - Trading session
- \eason_codes\ - Array of reason codes
- \summary\ - Human summary
- \payload\ - Full JSON data

**bot_latest_snapshot** - Current state per device
- \device_id\ (PRIMARY KEY)
- \last_seq\ - Event sequence number
- \snapshot\ - Full state as JSONB
- \updated_at\ - Last update timestamp

**bot_health** - Health metrics
- \device_id\ (PRIMARY KEY)
- \mode\ - OBSERVE, PAPER, LIVE
- \kill_switch\ - ARMED, TRIPPED
- \eed_latency_ms\ - Data feed latency
- \missing_bars\ - Missing OHLC bars
- \clock_drift_ms\ - Clock drift from server
- \
otes\ - Free-form notes
- \updated_at\ - Last update

---

##  Security Summary

### Access Control (RLS Policies)

**Anonymous Users (UI Clients):**
-  Can READ all tables
-  Cannot write anything
-  Get Realtime updates automatically

**Service Role (Publisher via Edge Function):**
-  Cannot read directly
-  Can execute functions to write data
-  Complete audit trail maintained

### Function API (for Publisher)

\\\sql
register_bot_device(device_id, name)  BOOLEAN
insert_bot_event(device_id, seq, event_id, ts, type, ...)  BOOLEAN
update_bot_snapshot(device_id, seq, snapshot)  BOOLEAN
update_bot_health(device_id, mode, kill_switch, ...)  BOOLEAN
\\\

---

##  What's Next

1.  **Deploy migrations** (this checklist)
2.  **Get API keys** (see above)
3.  **Configure Netlify** (add env vars)
4.  **Deploy UI to Netlify** (auto from git)
5.  **Configure Publisher** (if using local bot)
6.  **Test Realtime** (browser console)

---

##  Common Issues

| Issue | Solution |
|-------|----------|
| "Permission denied for schema public" | Ensure you're using **Service Role** key for deployments |
| "Table already exists" | That's fine! \IF NOT EXISTS\ handles it |
| "Function execute permission denied" | Service role must be granted EXECUTE |
| "Realtime updates not working" | Check tables are in \pg_publication_tables\ |
| "Cannot insert into bot_events" | Use \insert_bot_event()\ function, not direct INSERT |

---

##  Quick Reference

**Files to copy for deployment:**
- \supabase/migrations/20251218_phase2.sql\
- \supabase/migrations/20251218_rls_policies.sql\
- \supabase/migrations/20251219_realtime_subscriptions.sql\
- \supabase/migrations/20251219_publisher_functions.sql\
- \supabase/migrations/20251219_audit_and_retention.sql\

**Documentation:**
- Full details: \supabase/migrations/README.md\
- Quick start: \supabase/README.md\

**Git commit:**
- \95df2554\ - All migrations added and pushed

---

**Status:**  All migrations created, committed, and ready for deployment
