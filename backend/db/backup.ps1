<#
.SYNOPSIS
    Takes a compressed backup of the dockerized AANGA database.

.DESCRIPTION
    Writes db/backups/aanga-<timestamp>.dump using pg_dump inside the container.
    Custom format, so restore.ps1 can restore selectively and in parallel.

    Supabase took backups for you. Self-hosting means this is now your job:
    schedule it (Task Scheduler on Windows, cron on a VPS) and -- the part
    people skip -- actually run restore.ps1 against a scratch database once,
    so you know the backups are readable before you need them.

.PARAMETER Keep
    Number of recent backups to retain. Older ones are deleted. Default 14.

.EXAMPLE
    .\db\backup.ps1
.EXAMPLE
    .\db\backup.ps1 -Keep 30
#>
[CmdletBinding()]
param([int]$Keep = 14)

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

if (-not (Test-Path $BackupDir)) { New-Item -ItemType Directory -Path $BackupDir | Out-Null }

$name = "aanga-$(Get-Date -Format 'yyyyMMdd-HHmmss').dump"
Write-Host "==> Backing up $pgDb -> db/backups/$name" -ForegroundColor Cyan

# No shell wrapper: every argument is a simple token, so this avoids the
# quoting minefield of passing a script through sh -c from PowerShell.
docker compose -f $ComposeFile exec -T db `
    pg_dump -U $pgUser -d $pgDb --format=custom --compress=9 --file=/backups/$name
if ($LASTEXITCODE -ne 0) { throw 'pg_dump failed' }

$file = Get-Item (Join-Path $BackupDir $name)
Write-Host ("    OK -- {0:N1} MB" -f ($file.Length / 1MB)) -ForegroundColor Green

# Retention. Only touches this script's own naming pattern, so migration dumps
# (supabase-*.dump) are never swept up.
$old = Get-ChildItem $BackupDir -Filter 'aanga-*.dump' |
       Sort-Object LastWriteTime -Descending |
       Select-Object -Skip $Keep
foreach ($f in $old) {
    Remove-Item $f.FullName -Force
    Write-Host "    pruned $($f.Name)" -ForegroundColor DarkGray
}
