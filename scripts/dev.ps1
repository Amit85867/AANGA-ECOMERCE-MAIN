<#
.SYNOPSIS
    Start the whole AANGA stack for local development, in the right order.

.DESCRIPTION
    1. checks the Neon dev branch is reachable (no local database to start)
    2. applies any pending database migrations      (flask apply-migrations)
    3. the API on http://127.0.0.1:5000              (its own window)
    4. the storefront on http://localhost:5173       (its own window)

    Each step is checked before the next one starts, and a server that is
    already running is reused rather than started twice.

    From the repository root:

        powershell -ExecutionPolicy Bypass -File scripts\dev.ps1

    -Stop        stop the API and storefront started here (the database keeps running)
    -NoFrontend  start the database and API only
#>
param([switch]$Stop, [switch]$NoFrontend)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = Join-Path $backend 'venv\Scripts\python.exe'

function Say($text) { Write-Host "==> $text" -ForegroundColor Cyan }
function Fail($text) { Write-Host "ERROR: $text" -ForegroundColor Red; exit 1 }

function Listener($port) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
}

function Stop-Port($port) {
    # The dev servers run as a small tree of processes (launcher, reloader,
    # worker). Stopping only the one that owns the port leaves the others
    # behind, holding it; this stops the whole tree.
    $seen = @{}
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        $id = $_.OwningProcess
        if ($id -and -not $seen[$id]) {
            $seen[$id] = $true
            & taskkill /PID $id /T /F 2>$null | Out-Null
        }
    }
}

function Wait-Url($url, $seconds) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) { return $true }
        } catch { }
        Start-Sleep -Milliseconds 700
    }
    return $false
}

if ($Stop) {
    Say 'Stopping the API (5000) and the storefront (5173)'
    Stop-Port 5000
    Stop-Port 5173
    Write-Host 'Stopped. The Neon database is unaffected.'
    exit 0
}

# -- 0. What has to be there already --------------------------
if (-not (Test-Path (Join-Path $backend '.env'))) { Fail 'backend\.env is missing. Copy backend\.env.example to backend\.env and fill it in.' }
if (-not (Test-Path $python)) {
    Say 'Creating the Python virtual environment (first run only)'
    & python -m venv (Join-Path $backend 'venv')
    & $python -m pip install --quiet -r (Join-Path $backend 'requirements-dev.txt')
    if ($LASTEXITCODE -ne 0) { Fail 'Could not install the Python packages.' }
}
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Say 'Installing the storefront packages (first run only)'
    Push-Location $frontend; & npm ci; $code = $LASTEXITCODE; Pop-Location
    if ($code -ne 0) { Fail 'npm ci failed.' }
}

# -- 1. Database ----------------------------------------------
# Neon is always there; nothing to start. The first query after five quiet
# minutes wakes the compute and takes about a second.
Say 'Checking the Neon dev branch is reachable'
Push-Location $backend
& $py -c @'
import os, sys
from dotenv import load_dotenv
import psycopg2
load_dotenv(".env")
url = os.environ.get("DATABASE_URL")
if not url:
    sys.exit("DATABASE_URL is not set in backend/.env (see docs/DATABASE.md).")
try:
    psycopg2.connect(url, connect_timeout=30).close()
except Exception as exc:
    sys.exit(f"Cannot reach the database: [{type(exc).__name__}] see docs/DATABASE.md")
'@
$code = $LASTEXITCODE
Pop-Location
if ($code -ne 0) { Fail 'The Neon dev branch is not reachable (message above).' }

# -- 2. Migrations --------------------------------------------
Say 'Applying database migrations'
Push-Location $backend
& $python -m flask --app run apply-migrations
$code = $LASTEXITCODE
Pop-Location
if ($code -ne 0) { Fail 'Migrations failed (message above). Nothing else was started.' }

# -- 3. API ---------------------------------------------------
if (Listener 5000) {
    if (Wait-Url 'http://127.0.0.1:5000/api/health' 5) {
        Say 'The API is already running on port 5000: using it'
    } else {
        Fail 'Something is using port 5000 but it is not answering as the API. Run: scripts\dev.ps1 -Stop   and start again.'
    }
} else {
    Say 'Starting the API (new window)'
    Start-Process powershell -WorkingDirectory $backend -ArgumentList '-NoExit', '-Command', "`$host.UI.RawUI.WindowTitle = 'AANGA API'; & '$python' run.py"
    if (-not (Wait-Url 'http://127.0.0.1:5000/api/health' 60)) { Fail 'The API did not start. Look at the "AANGA API" window for the reason.' }
}

# The API is up: is it actually serving the catalogue?
try {
    $listing = Invoke-RestMethod -Uri 'http://127.0.0.1:5000/api/products?per_page=1' -TimeoutSec 20
    Write-Host ("    API ok - {0} products in the catalogue" -f $listing.total)
} catch {
    Fail "The API is running but /api/products failed: $($_.Exception.Message). Look at the `"AANGA API`" window."
}

# -- 4. Storefront --------------------------------------------
if (-not $NoFrontend) {
    if (Listener 5173) {
        Say 'The storefront is already running on port 5173: using it'
    } else {
        Say 'Starting the storefront (new window)'
        Start-Process powershell -WorkingDirectory $frontend -ArgumentList '-NoExit', '-Command', "`$host.UI.RawUI.WindowTitle = 'AANGA storefront'; npm run dev"
        if (-not (Wait-Url 'http://localhost:5173/' 60)) { Fail 'The storefront did not start. Look at the "AANGA storefront" window.' }
    }
}

Write-Host ''
Write-Host 'Ready.' -ForegroundColor Green
Write-Host '  Storefront  http://localhost:5173'
Write-Host '  Admin       http://localhost:5173/admin'
Write-Host '  API         http://127.0.0.1:5000/api/health'
Write-Host '  Stop        powershell -ExecutionPolicy Bypass -File scripts\dev.ps1 -Stop'
