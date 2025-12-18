# Supabase Migrations - Trading Bot Phase 2

## Overview

This directory contains all database migrations for the Trading Bot Supabase cloud mirror. Migrations are applied in order and are idempotent (safe to run multiple times).

## Migration Files

### 1. `20251218_phase2.sql` - Core Schema
**Depends on:** Nothing (initial schema)
**Creates:**
- `bot_devices` - Device registry with creation/last-seen timestamps
- `bot_events` - Event stream from trading bot with full timeline
- `bot_latest_snapshot` - Current state snapshot per device
- `bot_health` - Health metrics and operational status

**Indexes:**
- `bot_events_device_ts_idx` - For timeline queries by device
- `bot_events_type_idx` - For filtering by event type
- `bot_events_reason_codes_idx` - GIN index for reason code filtering

---

### 2. `20251218_rls_policies.sql` - Row-Level Security
**Depends on:** `20251218_phase2.sql`
**Enables:**
- RLS on all tables
- Read-only access for anonymous users (UI clients)
- Write access restricted to service role only (publisher)
- Automatic policy enforcement

**Security Model:**
```
UI Client (Anon)     → Can READ all tables
Publisher (Service)  → Can INSERT/UPDATE/DELETE (write only)
Netlify/Browser      → Authenticated or anon, read-only via Realtime
```

---

### 3. `20251219_realtime_subscriptions.sql` - Live Updates
**Depends on:** `20251218_rls_policies.sql`
**Enables:**
- Realtime publication on `bot_events` (live timeline)
- Realtime publication on `bot_latest_snapshot` (live state)
- Realtime publication on `bot_health` (live monitoring)

**Subscriptions available:**
```typescript
// Timeline
supabase.channel('bot-events')
  .on('postgres_changes', { event: 'INSERT', table: 'bot_events' }, handle)
  .subscribe();

// State
supabase.channel('bot-snapshot')
  .on('postgres_changes', { event: '*', table: 'bot_latest_snapshot' }, handle)
  .subscribe();

// Health
supabase.channel('bot-health')
  .on('postgres_changes', { event: '*', table: 'bot_health' }, handle)
  .subscribe();
```

---

### 4. `20251219_publisher_functions.sql` - Publisher API
**Depends on:** `20251218_phase2.sql`
**Creates PL/pgSQL functions:**
- `register_bot_device(device_id, name)` - Register/heartbeat bot
- `insert_bot_event(...)` - Insert event with full payload
- `update_bot_snapshot(device_id, seq, snapshot)` - Update state snapshot
- `update_bot_health(device_id, mode, kill_switch, ...)` - Update health metrics

**Usage (from Edge Function):**
```sql
SELECT register_bot_device('bot-01', 'Trading Bot #1');
SELECT insert_bot_event('bot-01', 1, 'evt-001', NOW(), 'SIGNAL', ...);
SELECT update_bot_snapshot('bot-01', 100, '{...}'::jsonb);
SELECT update_bot_health('bot-01', 'LIVE', 'ARMED', ...);
```

---

### 5. `20251219_audit_and_retention.sql` - Audit & Cleanup
**Depends on:** `20251218_phase2.sql`
**Creates:**
- `bot_audit_log` - Audit trail of all writes
- `log_bot_events_insert()` trigger - Auto-logs event inserts
- `log_bot_health_update()` trigger - Auto-logs health updates
- `cleanup_old_events(days)` function - Manual data retention cleanup

**Usage:**
```sql
-- Delete events older than 30 days
SELECT cleanup_old_events(30);

-- Query audit log
SELECT * FROM bot_audit_log WHERE device_id = 'bot-01' ORDER BY recorded_at DESC LIMIT 100;
```

---

## Deployment Instructions

### Option 1: Supabase Dashboard (Recommended)

1. **Go to SQL Editor** in your Supabase project
2. **Copy the entire contents of each migration file**
3. **Paste into new query** and click "Execute"
4. **Order matters** - execute in numeric order:
   - `20251218_phase2.sql` first
   - Then `20251218_rls_policies.sql`
   - Then `20251219_realtime_subscriptions.sql`
   - Then `20251219_publisher_functions.sql`
   - Finally `20251219_audit_and_retention.sql`

---

### Option 2: Supabase CLI

```bash
# Install Supabase CLI (if not already)
npm install -g @supabase/cli

# Link to your project
supabase link --project-id YOUR_PROJECT_ID

# Push all migrations
supabase db push

# Verify
supabase db pull  # Downloads current schema
```

---

### Option 3: Direct psql (if you have CLI access)

```bash
# Get your database connection string from Supabase dashboard
psql "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" < migrations/20251218_phase2.sql
psql "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" < migrations/20251218_rls_policies.sql
# ... repeat for others
```

---

## Verification Checklist

After running migrations, verify:

```sql
-- 1. Tables exist
SELECT tablename FROM pg_tables WHERE schemaname = 'public';

-- 2. RLS is enabled
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';

-- 3. Realtime is enabled
SELECT * FROM pg_publication_tables WHERE pubname = 'supabase_realtime';

-- 4. Functions exist
SELECT proname FROM pg_proc WHERE pronamespace = 'public'::regnamespace;

-- 5. Audit triggers exist
SELECT trigger_name FROM information_schema.triggers WHERE event_object_schema = 'public';

-- 6. Insert test device
SELECT register_bot_device('test-device-001', 'Test Device');

-- 7. Verify it's there
SELECT * FROM bot_devices WHERE device_id = 'test-device-001';
```

---

## Rollback Instructions

If something goes wrong, Supabase allows you to:

1. **Check migration history**
   - Supabase dashboard → Migrations tab
   
2. **View migration details**
   - Each migration is timestamped and reversible
   
3. **Drop tables manually (last resort)**
   ```sql
   DROP TABLE bot_audit_log;
   DROP TABLE bot_health;
   DROP TABLE bot_latest_snapshot;
   DROP TABLE bot_events;
   DROP TABLE bot_devices;
   ```

---

## Production Notes

### Performance Tuning
- `bot_events` table grows rapidly (~100-1000 events/day per bot)
- Use `cleanup_old_events(30)` weekly to maintain performance
- Consider partitioning by `device_id` + date if > 1M rows

### Monitoring
- Check `bot_audit_log` for write patterns
- Monitor `pg_stat_statements` for slow queries
- Set up alerts on `bot_health` for critical status changes

### Scaling
- Connection pooling recommended (Supabase handles this automatically)
- Enable compression on `payload` JSONB to reduce storage
- Archive old events to cold storage after 90 days if needed

---

## Support

For issues:
1. Check Supabase dashboard logs
2. Verify RLS policies aren't blocking access
3. Ensure Edge Functions are using service role key (not anon key)
4. Test Realtime subscriptions in browser console

Example test:
```typescript
const { data } = await supabase
  .from('bot_events')
  .select('*')
  .limit(1);
console.log('Read access:', !!data);  // Should be true
```
