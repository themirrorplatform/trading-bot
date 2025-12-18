#!/bin/bash
# Deploy all Supabase migrations to project
# Usage: ./deploy.sh https://project.supabase.co postgres_password

PROJECT_URL=$1
DB_PASSWORD=$2
PROJECT_ID=$(echo $PROJECT_URL | grep -oE '[a-z]+\.[a-z]+\.co' | cut -d. -f1)

if [ -z "$PROJECT_URL" ] || [ -z "$DB_PASSWORD" ]; then
  echo "Usage: ./deploy.sh https://project.supabase.co YOUR_DB_PASSWORD"
  exit 1
fi

echo "🚀 Deploying migrations to Supabase project..."

# Extract project ID and host
HOST=$(echo $PROJECT_URL | sed 's/https:\/\///g')

# Connection string
DB_URL="postgresql://postgres:${DB_PASSWORD}@${HOST}:5432/postgres"

# Run migrations in order
echo "📦 Running: 20251218_phase2.sql..."
psql "$DB_URL" -f 20251218_phase2.sql

echo "🔒 Running: 20251218_rls_policies.sql..."
psql "$DB_URL" -f 20251218_rls_policies.sql

echo "⚡ Running: 20251219_realtime_subscriptions.sql..."
psql "$DB_URL" -f 20251219_realtime_subscriptions.sql

echo "🔧 Running: 20251219_publisher_functions.sql..."
psql "$DB_URL" -f 20251219_publisher_functions.sql

echo "📋 Running: 20251219_audit_and_retention.sql..."
psql "$DB_URL" -f 20251219_audit_and_retention.sql

echo ""
echo "✅ All migrations deployed successfully!"
echo ""
echo "Verify with:"
echo "  SELECT COUNT(*) FROM bot_devices;"
echo "  SELECT COUNT(*) FROM pg_publication_tables WHERE pubname = 'supabase_realtime';"
