# Supabase Configuration for Trading Bot

This directory contains the database schema and migrations for the trading bot's cloud mirror in Supabase.

## Quick Start

1. **Create Supabase Project**
   - Go to https://supabase.com
   - Create new project in desired region
   - Note your project URL and database password

2. **Deploy Schema**
   - Open Supabase dashboard  SQL Editor
   - Copy each migration file content in order:
     1. migrations/20251218_phase2.sql - Core schema (tables + indexes)
     2. migrations/20251218_rls_policies.sql - Row-level security for Anon/Service roles
     3. migrations/20251219_realtime_subscriptions.sql - Enable Realtime on tables
     4. migrations/20251219_publisher_functions.sql - Functions for publisher writes
     5. migrations/20251219_audit_and_retention.sql - Audit log + cleanup functions

3. **Get Credentials**
   - API URL: Project Settings  API
   - Anon Key: Project Settings  API  Anon public
   - Service Role Key: Project Settings  API  Service role secret (keep this safe!)

4. **Configure Environment**
   `ash
   # In ui/.env
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=eyJhbGciOi...
   `

## Files

- **schema.sql** - Base schema (informational, see migrations/ for actual deployment)
- **migrations/** - All migrations in deployment order (5 files total)
- **migrations/README.md** - Detailed documentation for each migration

## Architecture

\\\
Trading Bot (Local)
    
Publisher (FastAPI Edge Function)
     (uses service_role key, writes only)
Supabase PostgreSQL
     (uses anon key + RLS, reads only)
Netlify UI (Browser)
    
User Dashboard (Realtime updates)
\\\

## Security Model

- **Anon users (UI)**: Read-only via RLS, Realtime subscriptions only
- **Service role (publisher)**: Writes only through stored functions
- **No direct table writes**: All data changes through PL/pgSQL functions
- **Audit trail**: All writes logged to bot_audit_log table

## Deployment Methods

See \migrations/README.md\ for detailed instructions:
- **Dashboard SQL Editor** (easiest, recommended for first-time)
- **Supabase CLI** (recommended for CI/CD automation)
- **Direct psql** (if CLI available)

## Migration Summary

| File | Purpose | Creates |
|------|---------|---------|
| 20251218_phase2.sql | Core schema | 4 tables, 3 indexes |
| 20251218_rls_policies.sql | Security | Anon read-only, service role write |
| 20251219_realtime_subscriptions.sql | Live updates | Realtime publication |
| 20251219_publisher_functions.sql | API | 4 PL/pgSQL functions for writes |
| 20251219_audit_and_retention.sql | Auditing | Audit log + cleanup functions |

## Quick Verification

After deploying, verify in Supabase SQL Editor:

\\\sql
-- Should return 4
SELECT COUNT(*) FROM pg_tables 
WHERE schemaname = 'public' AND tablename LIKE 'bot_%';

-- Should show 'on'
SELECT tablename, rowsecurity FROM pg_tables 
WHERE tablename LIKE 'bot_%';

-- Should return 3 tables
SELECT * FROM pg_publication_tables 
WHERE pubname = 'supabase_realtime';
\\\

## Support & Troubleshooting

1. **RLS blocking access?**  Check dashboard Logs for auth errors
2. **Realtime not working?**  Verify tables in \pg_publication_tables\
3. **Functions not executing?**  Check \pg_proc\ for function definitions
4. **Audit log missing?**  Verify triggers with \information_schema.triggers\

See migrations/README.md for complete troubleshooting guide.
