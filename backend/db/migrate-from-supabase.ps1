<#
.SYNOPSIS
    Copies the AANGA database out of Supabase into the local dockerized Postgres.

.DESCRIPTION
    Dumps the `public` schema (structure + all rows) from Supabase via the
    session pooler, then restores it into the `db` service defined in
    backend/docker-compose.yml.

    Everything runs inside the postgres:17 container, so no local pg_dump /
    pg_restore install is needed and the client version always matches the
    server the dump came from.

    Reads POOLER_DATABASE_URL, POSTGRES_USER and POSTGRES_DB from backend/.env.
    The Supabase database is only ever READ.

.PARAMETER DumpOnly
    Take the dump and stop. Nothing is written to the local database.

.PARAMETER RestoreOnly
    Skip the dump and restore an existing file from db/backups instead.
    Pass the file name, e.g. -RestoreOnly supabase-20260808-142530.dump

.PARAMETER Force
    Skip the "this will replace the local public schema" confirmation.

.EXAMPLE
    .\db\migrate-from-supabase.ps1
.EXAMPLE
    .\db\migrate-from-supabase.ps1 -DumpOnly
.EXAMPLE
    .\db\migrate-from-supabase.ps1 -RestoreOnly supabase-20260808-142530.dump
#>
[CmdletBinding()]
param(
    [switch]$DumpOnly,
    [string]$RestoreOnly,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$BackendDir = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $BackendDir 'docker-compose.yml'
$EnvFile = Join-Path $BackendDir '.env'
$BackupDir = Join-Path $PSScriptRoot 'backups'

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    $msg" -ForegroundColor Yellow }

# --- Read backend/.env -------------------------------------------------------
# Deliberately hand-rolled: python-dotenv is not guaranteed to be on PATH and
# we only need plain KEY=VALUE lines.
function Read-DotEnv($path) {
    $map = @{}
    if (-not (Test-Path $path)) { return $map }
    foreach ($line in Get-Content $path) {
        $trimmed = $line.Trim()
        if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }
        $idx = $trimmed.IndexOf('=')
        if ($idx -lt 1) { continue }
        $key = $trimmed.Substring(0, $idx).Trim()
        $val = $trimmed.Substring($idx + 1).Trim()
        if ($val.Length -ge 2) {
            if (($val.StartsWith('"') -and $val.EndsWith('"')) -or
                ($val.StartsWith("'") -and $val.EndsWith("'"))) {
                $val = $val.Substring(1, $val.Length - 2)
            }
        }
        $map[$key] = $val
    }
    return $map
}

# --- Preflight ---------------------------------------------------------------
Write-Step 'Checking prerequisites'

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker is not running. Start Docker Desktop and try again."
}
Write-Ok 'Docker daemon is up'

if (-not (Test-Path $ComposeFile)) { throw "Missing $ComposeFile" }
if (-not (Test-Path $EnvFile))     { throw "Missing $EnvFile (copy .env.example)" }

$dotenv = Read-DotEnv $EnvFile
$pgUser = $dotenv['POSTGRES_USER']
$pgDb   = $dotenv['POSTGRES_DB']
$pooler = $dotenv['POOLER_DATABASE_URL']

if (-not $pgUser) { throw "POSTGRES_USER is not set in backend/.env" }
if (-not $pgDb)   { throw "POSTGRES_DB is not set in backend/.env" }
if (-not $RestoreOnly -and -not $pooler) {
    throw @"
POOLER_DATABASE_URL is not set in backend/.env.

Supabase -> Project Settings -> Database -> Connection string -> "Session pooler".
The direct db.<ref>.supabase.co host is IPv6-only and unreachable from inside
a container, so the pooler URI is required here.
"@
}
Write-Ok "Target: $pgUser@$pgDb (container aanga-db)"

if (-not (Test-Path $BackupDir)) { New-Item -ItemType Directory -Path $BackupDir | Out-Null }

# --- Start the container -----------------------------------------------------
Write-Step 'Starting the local Postgres container'
docker compose -f $ComposeFile up -d db
if ($LASTEXITCODE -ne 0) { throw 'docker compose up failed' }

Write-Host '    waiting for healthy' -NoNewline
$healthy = $false
foreach ($i in 1..60) {
    $status = (docker inspect --format '{{.State.Health.Status}}' aanga-db 2>$null)
    if ($status -eq 'healthy') { $healthy = $true; break }
    Write-Host '.' -NoNewline
    Start-Sleep -Seconds 2
}
Write-Host ''
if (-not $healthy) {
    throw "Container did not become healthy. Inspect with: docker compose -f `"$ComposeFile`" logs db"
}
Write-Ok 'Container healthy'

# --- Dump from Supabase ------------------------------------------------------
if ($RestoreOnly) {
    $dumpName = $RestoreOnly
    if (-not (Test-Path (Join-Path $BackupDir $dumpName))) {
        throw "No such dump: $(Join-Path $BackupDir $dumpName)"
    }
    Write-Step "Reusing existing dump $dumpName"
} else {
    $dumpName = "supabase-$(Get-Date -Format 'yyyyMMdd-HHmmss').dump"
    Write-Step "Dumping Supabase public schema -> db/backups/$dumpName"
    Write-Warn 'Read-only on Supabase. Large catalogues can take a few minutes.'

    # Both the URL and the output path go in via -e: the password then never
    # lands in the container's process list, and the sh script stays a literal
    # single-quoted PowerShell string so nothing needs escaping.
    # --no-owner/--no-privileges drop Supabase-specific role ownership; the
    # custom format lets pg_restore reorder around foreign keys.
    docker compose -f $ComposeFile exec -T -e SRC_URL="$pooler" -e OUT="/backups/$dumpName" db `
        sh -c 'pg_dump "$SRC_URL" --schema=public --no-owner --no-privileges --format=custom --file="$OUT"'
    if ($LASTEXITCODE -ne 0) { throw 'pg_dump failed -- check POOLER_DATABASE_URL' }

    $size = (Get-Item (Join-Path $BackupDir $dumpName)).Length
    Write-Ok ("Dump written: {0:N1} MB" -f ($size / 1MB))
}

if ($DumpOnly) {
    Write-Step 'Done (-DumpOnly). Nothing was written to the local database.'
    Write-Host "    Restore later with: .\db\migrate-from-supabase.ps1 -RestoreOnly $dumpName"
    return
}

# --- Confirm the destructive half -------------------------------------------
if (-not $Force) {
    Write-Step 'About to REPLACE the local public schema'
    Write-Warn "Database '$pgDb' in container aanga-db will be wiped and rebuilt from $dumpName."
    Write-Warn 'Supabase is not touched.'
    $answer = Read-Host '    Type YES to continue'
    if ($answer -ne 'YES') { Write-Host '    Aborted.'; return }
}

# --- Restore -----------------------------------------------------------------
Write-Step 'Rebuilding the local schema'

# The dump carries its own CREATE SCHEMA public, so clear the existing one.
# The auth/extensions shims live outside public and survive; re-applying them
# is idempotent and covers a volume created before they existed.
docker compose -f $ComposeFile exec -T db `
    psql -v ON_ERROR_STOP=1 -U $pgUser -d $pgDb -c 'DROP SCHEMA IF EXISTS public CASCADE;'
if ($LASTEXITCODE -ne 0) { throw 'Failed to drop the public schema' }

docker compose -f $ComposeFile exec -T db `
    psql -v ON_ERROR_STOP=1 -U $pgUser -d $pgDb -f /docker-entrypoint-initdb.d/01_supabase_compat.sql
if ($LASTEXITCODE -ne 0) { throw 'Failed to apply the Supabase compatibility shims' }
Write-Ok 'public dropped, shims applied'

Write-Step 'Restoring data'
# Connects over the unix socket (no -h), which the official image trusts, so
# no password is needed inside the container.
# Not --exit-on-error: a dump from a managed provider usually emits a few
# benign errors (COMMENT ON EXTENSION, event triggers we cannot own). Real
# failures are caught by the row-count check below.
docker compose -f $ComposeFile exec -T db `
    pg_restore --no-owner --no-privileges -U $pgUser -d $pgDb /backups/$dumpName
if ($LASTEXITCODE -ne 0) {
    Write-Warn 'pg_restore reported errors -- review the output above before trusting this database.'
}

docker compose -f $ComposeFile exec -T db `
    psql -U $pgUser -d $pgDb -c 'ANALYZE;' | Out-Null

# --- Outstanding migrations --------------------------------------------------
# The restored dump reflects whatever state the LIVE Supabase database is in,
# which is not necessarily what schema.sql (the canonical DDL) describes. The
# payment-integrity guards in particular were never applied to Supabase, so a
# straight dump/restore would silently drop them. Re-applying is safe: the file
# is written with IF NOT EXISTS guards throughout.
Write-Step 'Applying outstanding migrations'

$pendingMigrations = @('migrations_orders_idempotency.sql', 'migrations_address_archive.sql', 'migrations_ops_tables.sql', 'migrations_admin_ops.sql')
foreach ($m in $pendingMigrations) {
    $src = Join-Path $BackendDir $m
    if (-not (Test-Path $src)) { Write-Warn "skipped (not found): $m"; continue }

    # Staged through the mounted backups directory so the container can read it.
    $staged = Join-Path $BackupDir '_migration.sql'
    Copy-Item $src $staged -Force

    docker compose -f $ComposeFile exec -T db `
        psql -v ON_ERROR_STOP=1 -U $pgUser -d $pgDb -f /backups/_migration.sql | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "FAILED: $m"
        Write-Warn 'A unique index here fails if the restored data already violates it. Check with:'
        Write-Warn '  SELECT payment_ref, count(*) FROM orders WHERE payment_ref IS NOT NULL'
        Write-Warn '  GROUP BY payment_ref HAVING count(*) > 1;'
    } else {
        Write-Ok "applied: $m"
    }
    Remove-Item $staged -ErrorAction SilentlyContinue
}

# --- Verify ------------------------------------------------------------------
Write-Step 'Verifying row counts (local vs Supabase)'

# query_to_xml gives an exact count per table in a single round trip;
# pg_stat_user_tables would only give estimates until autovacuum catches up.
$countSql = @'
SELECT table_name,
       (xpath('/row/c/text()',
              query_to_xml(format('select count(*) as c from %I.%I', table_schema, table_name),
                           false, true, '')))[1]::text::bigint AS rows
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;
'@

$sqlPath = Join-Path $BackupDir '_rowcounts.sql'
Set-Content -Path $sqlPath -Value $countSql -Encoding ascii

$localCounts = docker compose -f $ComposeFile exec -T db `
    psql -U $pgUser -d $pgDb -At -F '|' -f /backups/_rowcounts.sql

if ($RestoreOnly) {
    Write-Host ($localCounts -join "`n")
    Write-Warn 'Restored from a file -- no live Supabase comparison performed.'
} else {
    $srcCounts = docker compose -f $ComposeFile exec -T -e SRC_URL="$pooler" db `
        sh -c 'psql "$SRC_URL" -At -F "|" -f /backups/_rowcounts.sql'

    $srcMap = @{}
    foreach ($row in $srcCounts) {
        if ($row -match '^(.+)\|(\d+)$') { $srcMap[$Matches[1]] = [int]$Matches[2] }
    }

    $mismatch = 0
    Write-Host ''
    Write-Host ('    {0,-34} {1,10} {2,10}' -f 'table', 'supabase', 'local')
    Write-Host ('    ' + ('-' * 56))
    foreach ($row in $localCounts) {
        if ($row -notmatch '^(.+)\|(\d+)$') { continue }
        $table = $Matches[1]
        $localN = [int]$Matches[2]
        $srcN = -1
        if ($srcMap.ContainsKey($table)) { $srcN = $srcMap[$table] }

        $line = '    {0,-34} {1,10} {2,10}' -f $table, $srcN, $localN
        if ($srcN -eq $localN) {
            Write-Host $line -ForegroundColor Green
        } else {
            Write-Host ($line + '   MISMATCH') -ForegroundColor Red
            $mismatch++
        }
    }
    Write-Host ''
    if ($mismatch -gt 0) {
        Write-Warn "$mismatch table(s) do not match. Do NOT switch DATABASE_URL yet."
    } else {
        Write-Ok 'Every table matches.'
    }
}

Remove-Item $sqlPath -ErrorAction SilentlyContinue

Write-Step 'Next step'
Write-Host @"
    Point the app at the container by editing backend/.env:

      DATABASE_URL=postgresql://${pgUser}:<POSTGRES_PASSWORD>@localhost:$(if ($dotenv['POSTGRES_PORT']) { $dotenv['POSTGRES_PORT'] } else { '55433' })/${pgDb}

    Keep the old Supabase URI around (as SUPABASE_DATABASE_URL) until you are
    confident -- switching back is then a one-line edit.
"@
