# Supabase Cloud Mirror (Phase 2)

This folder contains the cloud schema and migration files to mirror sanitized trading bot events, snapshots, and health to Supabase for anywhere-access dashboards.

## What's included
- `migrations/20251218_phase2.sql` – tables: `bot_devices`, `bot_events`, `bot_latest_snapshot`, `bot_health`
- `schema.sql` – same DDL as a single-file reference

## Apply the migration (choose 1)

### Option A — Supabase SQL Editor (quickest)
1. Open your project at https://app.supabase.com → Database → SQL Editor.
2. Paste the contents of `supabase/migrations/20251218_phase2.sql`.
3. Run → verify tables exist under Database → Tables.

### Option B — psql (if you have the DB URL)
1. Set environment variable `SUPABASE_DB_URL` to the project's Postgres URL:
   - Format: `postgresql://postgres:<PASSWORD>@db.<ref>.supabase.co:5432/postgres`
2. Run:
   ```powershell
   $env:PGOPTIONS='-c client_min_messages=warning'
   psql $env:SUPABASE_DB_URL -f .\supabase\migrations\20251218_phase2.sql
   ```

### Option C — Supabase CLI (remote db push)
1. Install CLI: https://supabase.com/docs/guides/cli
2. Login with a personal access token: `supabase login`
3. Link: `supabase link --project-ref <your-ref>`
4. Push: `supabase db push` (ensure migration exists in `supabase/migrations/`)

Note: The CLI uses your Supabase account token (not anon/service keys).

## Next steps
- Enable Realtime for `bot_events`, `bot_latest_snapshot`, `bot_health` in the Supabase UI.
- Create an Edge Function `mirror-events` to receive batches from the publisher and upsert into these tables.
- Configure the publisher (`publisher/config.json`) with your function URL and shared secret.

## Security
- Do NOT commit secrets.
- The publisher should use a shared secret validated by your Edge Function, not the anon key.
- UI in cloud mode should use the anon key with RLS rules that permit read-only access to your data.
