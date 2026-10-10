<#
.SYNOPSIS
    Restores a backup into the dockerized AANGA database. Destructive.

.DESCRIPTION
    Drops the `public` schema, re-applies the Supabase compatibility shims and
    restores the named dump from db/backups.

.PARAMETER File
    Dump file name inside db/backups. Omit to use the most recent aanga-*.dump.

.PARAMETER Force
    Skip the confirmation prompt.

.EXAMPLE
    .\db\restore.ps1
.EXAMPLE
    .\db\restore.ps1 -File aanga-20260808-030000.dump
#>
[CmdletBinding()]
param(
    [string]$File,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$BackendDir = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $BackendDir 'docker-compose.yml'
$EnvFile = Join-Path $BackendDir '.env'
$BackupDir = Join-Path $PSScriptRoot 'backups'

function Get-DotEnvValue($path, $key) {
    if (-not (Test-Path $path)) { return $null }
    foreach ($line in Get-Content $path) {
        $t = $line.Trim()
        if ($t -eq '' -or $t.StartsWith('#')) { continue }
        $i = $t.IndexOf('=')
        if ($i -lt 1) { continue }
        if ($t.Substring(0, $i).Trim() -eq $key) { return $t.Substring($i + 1).Trim().Trim('"', "'") }
    }
    return $null
}

$pgUser = Get-DotEnvValue $EnvFile 'POSTGRES_USER'
$pgDb   = Get-DotEnvValue $EnvFile 'POSTGRES_DB'
if (-not $pgUser -or -not $pgDb) { throw 'POSTGRES_USER / POSTGRES_DB missing from backend/.env' }

if (-not $File) {
    $latest = Get-ChildItem $BackupDir -Filter 'aanga-*.dump' -ErrorAction SilentlyContinue |
              Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) { throw "No aanga-*.dump found in $BackupDir -- pass -File explicitly." }
    $File = $latest.Name
}
if (-not (Test-Path (Join-Path $BackupDir $File))) { throw "No such dump: $File" }

if (-not $Force) {
    Write-Host "==> This REPLACES everything in database '$pgDb' with $File" -ForegroundColor Yellow
    if ((Read-Host '    Type YES to continue') -ne 'YES') { Write-Host '    Aborted.'; return }
}

Write-Host "==> Restoring $File" -ForegroundColor Cyan

docker compose -f $ComposeFile exec -T db `
    psql -v ON_ERROR_STOP=1 -U $pgUser -d $pgDb -c 'DROP SCHEMA IF EXISTS public CASCADE;'
if ($LASTEXITCODE -ne 0) { throw 'Failed to drop the public schema' }

docker compose -f $ComposeFile exec -T db `
    psql -v ON_ERROR_STOP=1 -U $pgUser -d $pgDb -f /docker-entrypoint-initdb.d/01_supabase_compat.sql
if ($LASTEXITCODE -ne 0) { throw 'Failed to apply the Supabase compatibility shims' }

docker compose -f $ComposeFile exec -T db `
    pg_restore --no-owner --no-privileges -U $pgUser -d $pgDb /backups/$File
if ($LASTEXITCODE -ne 0) {
    Write-Host '    pg_restore reported errors -- review the output above.' -ForegroundColor Yellow
} else {
    Write-Host '    OK' -ForegroundColor Green
}

docker compose -f $ComposeFile exec -T db psql -U $pgUser -d $pgDb -c 'ANALYZE;' | Out-Null
