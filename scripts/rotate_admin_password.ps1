<#
.SYNOPSIS
    Change the master admin's password on a Neon branch, with a hidden prompt.

.DESCRIPTION
    The bash version of this prompts through Python, and under Git Bash (mintty)
    native Windows Python cannot hide the input -- the password is echoed. This
    reads it with PowerShell's own Read-Host -AsSecureString instead, which
    hides it properly, and hands it to the CLI through a process-only
    environment variable.

    The password is never a command-line argument, so it does not reach your
    PowerShell history, and never a file. The database connection string is
    fetched from neonctl into this process only.

    ADMIN_PASSWORD is deliberately overwritten for the child process:
    backend/.env defines it, the CLI uses that value when present, and without
    this the "rotation" would silently re-apply the OLD password and look like
    it had worked.

.PARAMETER Branch
    production, dev or test.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\rotate_admin_password.ps1 production
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('production', 'dev', 'test')]
    [string]$Branch
)

$ErrorActionPreference = 'Stop'

function Say  { param($m) Write-Host "==> $m" -ForegroundColor Cyan }
function Fail { param($m) Write-Host "ERROR: $m" -ForegroundColor Red; exit 1 }

$root    = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$envFile = Join-Path $backend '.env'

$projectId = if ($env:NEON_PROJECT_ID) { $env:NEON_PROJECT_ID } else { 'dry-base-24522506' }
$orgId     = if ($env:NEON_ORG_ID)     { $env:NEON_ORG_ID }     else { 'org-long-mud-04364433' }

# ── The interpreter ───────────────────────────────────────────────────────
$py = Join-Path $backend 'venv\Scripts\python.exe'
if (-not (Test-Path $py)) { Fail "No virtualenv at $py. Create it and install requirements-dev.txt." }

# ── neonctl ───────────────────────────────────────────────────────────────
$neon = (Get-Command neonctl -ErrorAction SilentlyContinue).Source
if (-not $neon) { $neon = Join-Path $env:APPDATA 'npm\neonctl.cmd' }
if (-not (Test-Path $neon)) { Fail 'neonctl is not installed. Run: npm install -g neonctl' }

# ── Which admin ───────────────────────────────────────────────────────────
if (-not (Test-Path $envFile)) { Fail "backend/.env is missing." }
$adminEmail = $null
foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*ADMIN_EMAIL\s*=\s*(.+?)\s*$') { $adminEmail = $Matches[1]; break }
}
if (-not $adminEmail) { Fail 'No ADMIN_EMAIL in backend/.env.' }

# ── The connection string (this process only) ─────────────────────────────
Say "Fetching the $Branch connection string"
$dbUrl = & $neon connection-string $Branch --project-id $projectId --org-id $orgId `
            --role-name aanga_owner --database-name aanga
if ($LASTEXITCODE -ne 0 -or -not $dbUrl) {
    Fail "neonctl could not return a connection string for '$Branch'. Is it authenticated? (neonctl auth)"
}
$dbUrl = ($dbUrl | Select-Object -First 1).Trim()

Write-Host ''
Write-Host "  Branch : $Branch"      -ForegroundColor White
Write-Host "  Admin  : $adminEmail"  -ForegroundColor White
Write-Host ''

# ── The password, read with a properly hidden prompt ──────────────────────
function Read-Plain { param($Prompt)
    $secure = Read-Host -Prompt $Prompt -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

$pw1 = Read-Plain 'New password'
$pw2 = Read-Plain 'Confirm it'

if ($pw1 -cne $pw2)      { Fail 'The two entries do not match. Nothing was changed.' }
if ($pw1.Length -lt 12)  { Fail 'Use at least 12 characters. Nothing was changed.' }
if ($pw1 -eq 'AANGA@144amit') {
    Fail 'That is the password published in the git history. Choose a different one.'
}

# ── Run it ────────────────────────────────────────────────────────────────
$previousAdminPw = $env:ADMIN_PASSWORD
$previousDbUrl   = $env:DATABASE_URL
$previousFlask   = $env:FLASK_ENV
try {
    $env:ADMIN_PASSWORD = $pw1     # consumed by the CLI instead of its own prompt
    $env:DATABASE_URL   = $dbUrl
    $env:FLASK_ENV      = 'development'

    Say 'Updating the password'
    Push-Location $backend
    try {
        & $py -m flask --app run set-admin-password --email $adminEmail
        $code = $LASTEXITCODE
    } finally { Pop-Location }

    if ($code -ne 0) { Fail "The command exited with code $code. The password was NOT changed." }

    # ── Prove it actually took effect ─────────────────────────────────────
    # Re-reads the stored hash and checks the NEW password validates against
    # it. Without this, "no error" is not the same as "it changed".
    Say 'Verifying'
    $env:ADMIN_EMAIL_CHECK = $adminEmail
    # Written to a temp file rather than passed with -c: a multi-line argument
    # to a native executable is fragile under Windows quoting rules.
    $probe = Join-Path ([IO.Path]::GetTempPath()) ("aanga_verify_{0}.py" -f [guid]::NewGuid())
    @'
import os, sys
import psycopg2
from werkzeug.security import check_password_hash

conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=60)
cur = conn.cursor()
cur.execute("SELECT password_hash FROM admins WHERE email = %s",
            (os.environ["ADMIN_EMAIL_CHECK"],))
row = cur.fetchone()
conn.close()
if not row:
    print("MISSING")
    sys.exit(0)
print("OK" if check_password_hash(row[0], os.environ["ADMIN_PASSWORD"]) else "MISMATCH")
'@ | Set-Content -Path $probe -Encoding utf8

    Push-Location $backend
    try {
        $check = & $py $probe
        $checkCode = $LASTEXITCODE
    } finally {
        Pop-Location
        Remove-Item $probe -Force -ErrorAction SilentlyContinue
    }

    $verdict = ($check | Select-Object -Last 1)
    if ($checkCode -ne 0) {
        Write-Host 'WARNING: could not verify (the update itself reported success).' -ForegroundColor Yellow
    } elseif ($verdict -eq 'OK') {
        Write-Host ''
        Write-Host "SUCCESS: the password for $adminEmail on the '$Branch' branch is now the one you typed." -ForegroundColor Green
    } elseif ($verdict -eq 'MISSING') {
        Fail "No admin with email $adminEmail on '$Branch'."
    } else {
        Fail "The stored hash does not match what you typed. The password was NOT changed as expected."
    }
}
finally {
    $env:ADMIN_PASSWORD    = $previousAdminPw
    $env:DATABASE_URL      = $previousDbUrl
    $env:FLASK_ENV         = $previousFlask
    Remove-Item Env:\ADMIN_EMAIL_CHECK -ErrorAction SilentlyContinue
    $pw1 = $null; $pw2 = $null
    [GC]::Collect()
}
