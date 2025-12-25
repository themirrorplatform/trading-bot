#!/usr/bin/env python3
"""
Supabase Setup Script
Run migrations against Supabase project.

Usage:
    python scripts/setup_supabase.py

Requires:
    pip install supabase psycopg2-binary

Environment:
    SUPABASE_URL - Project URL
    SUPABASE_KEY - Service role key (not anon key for migrations)
    DATABASE_URL - Direct postgres connection string (optional, faster)
"""

import os
import sys
from pathlib import Path


def run_migrations_via_postgres():
    """Run migrations via direct postgres connection."""
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed. Run: pip install psycopg2-binary")
        return False

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        project_id = os.environ.get("SUPABASE_PROJECT_ID", "hhyilmbejidzriljesph")
        password = os.environ.get("SUPABASE_DB_PASSWORD")
        if not password:
            print("Set DATABASE_URL or SUPABASE_DB_PASSWORD env var")
            print(f"DATABASE_URL format: postgresql://postgres:[PASSWORD]@db.{project_id}.supabase.co:5432/postgres")
            return False
        database_url = f"postgresql://postgres:{password}@db.{project_id}.supabase.co:5432/postgres"

    migrations_dir = Path(__file__).parent.parent / "supabase" / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        print("No migration files found")
        return False

    print(f"Found {len(migration_files)} migration files")

    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()

        for migration_file in migration_files:
            print(f"Running: {migration_file.name}")
            sql = migration_file.read_text()
            try:
                cursor.execute(sql)
                print(f"  ✓ {migration_file.name}")
            except psycopg2.Error as e:
                if "already exists" in str(e):
                    print(f"  ⊘ {migration_file.name} (already applied)")
                else:
                    print(f"  ✗ {migration_file.name}: {e}")

        cursor.close()
        conn.close()
        print("\n✓ Migrations complete")
        return True

    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        return False


def print_manual_instructions():
    """Print instructions for manual setup."""
    migrations_dir = Path(__file__).parent.parent / "supabase" / "migrations"

    print("\n" + "=" * 60)
    print("MANUAL SETUP INSTRUCTIONS")
    print("=" * 60)
    print("\n1. Go to Supabase Dashboard: https://supabase.com/dashboard")
    print("2. Select your project: hhyilmbejidzriljesph")
    print("3. Navigate to: SQL Editor")
    print("4. Run each migration file in order:\n")

    for f in sorted(migrations_dir.glob("*.sql")):
        print(f"   - {f.name}")

    print("\n5. After running migrations, enable Realtime:")
    print("   - Go to Database > Replication")
    print("   - Enable replication for 'events' table")

    print("\n6. Set environment variables in Netlify:")
    print("   NEXT_PUBLIC_SUPABASE_URL=https://hhyilmbejidzriljesph.supabase.co")
    print("   NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>")

    print("\n" + "=" * 60)


def verify_tables():
    """Verify tables exist in Supabase."""
    try:
        from supabase import create_client
    except ImportError:
        print("supabase-py not installed. Run: pip install supabase")
        return False

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("Set SUPABASE_URL and SUPABASE_KEY env vars")
        return False

    client = create_client(url, key)

    tables = ["events", "trades", "daily_summary", "decision_journal"]
    print("\nVerifying tables...")

    for table in tables:
        try:
            result = client.table(table).select("*").limit(1).execute()
            print(f"  ✓ {table}")
        except Exception as e:
            print(f"  ✗ {table}: {e}")

    return True


if __name__ == "__main__":
    print("Supabase Setup for Trading Bot")
    print("-" * 40)

    # Try to load .env file
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        print(f"Loading {env_file}")
        for line in env_file.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_tables()
    elif len(sys.argv) > 1 and sys.argv[1] == "--manual":
        print_manual_instructions()
    else:
        if not run_migrations_via_postgres():
            print_manual_instructions()
