"""
Deploy Supabase migrations using direct SQL execution.
"""
import os
from pathlib import Path
import psycopg2
from urllib.parse import urlparse

# Supabase connection details
SUPABASE_URL = "https://hhyilmbejidzriljesph.supabase.co"
PROJECT_REF = "hhyilmbejidzriljesph"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhoeWlsbWJlamlkenJpbGplc3BoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NjAyMjQwMiwiZXhwIjoyMDgxNTk4NDAyfQ.5uAx5luloemwF4RKG6nIye4Cl6iy5xS07Z5Y2xsBTDo"

# Database connection URL (pooler)
DB_URL = f"postgresql://postgres.{PROJECT_REF}:[YOUR_DB_PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

def get_deployed_migrations(conn):
    """Check which migrations are already deployed."""
    with conn.cursor() as cur:
        # Check if migrations table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'schema_migrations'
            );
        """)
        exists = cur.fetchone()[0]
        
        if not exists:
            # Create migrations tracking table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    name TEXT,
                    executed_at TIMESTAMP DEFAULT NOW()
                );
            """)
            conn.commit()
            return set()
        
        # Get deployed migrations
        cur.execute("SELECT version FROM schema_migrations ORDER BY version;")
        return {row[0] for row in cur.fetchall()}

def get_local_migrations():
    """Get all local migration files."""
    migrations_dir = Path("supabase/migrations")
    migrations = []
    
    for file in sorted(migrations_dir.glob("*.sql")):
        if file.name in ["deploy.sh", "README.md"]:
            continue
        # Extract version from filename (first part before underscore)
        version = file.stem.split("_")[0]
        migrations.append((version, file.name, file))
    
    return migrations

def deploy_migration(conn, version, name, filepath):
    """Deploy a single migration file."""
    print(f"Deploying {name}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    with conn.cursor() as cur:
        try:
            # Execute migration
            cur.execute(sql)
            
            # Record in migrations table
            cur.execute(
                "INSERT INTO schema_migrations (version, name) VALUES (%s, %s) ON CONFLICT (version) DO NOTHING;",
                (version, name)
            )
            
            conn.commit()
            print(f"✓ Deployed {name}")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"✗ Failed to deploy {name}: {e}")
            return False

def main():
    """Main deployment function."""
    import sys
    
    # Get database password from command line arg or stdin
    if len(sys.argv) > 1:
        db_password = sys.argv[1]
    else:
        try:
            db_password = input("Enter your Supabase database password: ").strip()
        except EOFError:
            print("ERROR: Database password is required")
            return
    
    if not db_password:
        print("ERROR: Database password is required")
        return
    
    # Build connection URL (direct connection, not pooler)
    db_url = f"postgresql://postgres:{db_password}@db.{PROJECT_REF}.supabase.co:5432/postgres"
    
    print(f"Connecting to Supabase project: {PROJECT_REF}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(db_url)
        print("✓ Connected to database")
        
        # Get deployed migrations
        deployed = get_deployed_migrations(conn)
        print(f"\nCurrently deployed migrations: {len(deployed)}")
        if deployed:
            for v in sorted(deployed):
                print(f"  - {v}")
        
        # Get local migrations
        local_migrations = get_local_migrations()
        print(f"\nLocal migration files: {len(local_migrations)}")
        
        # Find migrations to deploy
        to_deploy = [(v, n, f) for v, n, f in local_migrations if v not in deployed]
        
        import sys
        if len(sys.argv) > 2 and sys.argv[2] == '--auto':
            confirm = 'yes'
            print("\nAuto-deploying migrations...")
        else:
            try:
                confirm = input("\nDeploy these migrations? (yes/no): ").strip().lower()
            except EOFError:
                confirm = 'yes'
                print("\nAuto-confirming deployment...")
        
            print("\n✓ All migrations are already deployed!")
            return
        
        print(f"\nMigrations to deploy: {len(to_deploy)}")
        for v, n, _ in to_deploy:
            print(f"  - {n}")
        
        # Confirm deployment
        confirm = input("\nDeploy these migrations? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("Deployment cancelled")
            return
        
        # Deploy migrations
        print("\nDeploying migrations...")
        success_count = 0
        for version, name, filepath in to_deploy:
            if deploy_migration(conn, version, name, filepath):
                success_count += 1
        
        print(f"\n{'='*60}")
        print(f"Deployment complete: {success_count}/{len(to_deploy)} migrations deployed")
        print(f"{'='*60}")
        
        conn.close()
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
