param(
  [string]$DbUrl = $env:SUPABASE_DB_URL,
  [string]$Migration = "$(Split-Path $MyInvocation.MyCommand.Path)/migrations/20251218_phase2.sql"
)

if (-not $DbUrl) {
  Write-Error "SUPABASE_DB_URL not set. Provide -DbUrl or set env var. Format: postgresql://postgres:<PASSWORD>@db.<ref>.supabase.co:5432/postgres"
  exit 1
}

if (-not (Test-Path $Migration)) {
  Write-Error "Migration file not found: $Migration"
  exit 1
}

Write-Host "Applying migration to $DbUrl ..."
$env:PGOPTIONS='-c client_min_messages=warning'
psql $DbUrl -f $Migration
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Migration applied successfully."