<#
.SYNOPSIS
    Upload the built storefront (frontend/dist) to Hostinger over FTPS.

.DESCRIPTION
    Hostinger's Single plan has no SSH, so this uses FTP with explicit TLS
    (FTPS) on port 21. Plain FTP would send your password across the internet
    in clear text; TLS is required here, not optional.

    The password is read with Read-Host -AsSecureString, so it is hidden as you
    type and never appears in history, a file, or this script's output.

    Upload order is deliberate: every asset first, index.html LAST. The assets
    have content-hashed names, so new ones sit alongside the old ones harmlessly
    until index.html switches the site over to them. Uploading index.html first
    would point visitors at assets that do not exist yet -- a blank page for the
    length of the upload.

    Nothing is deleted on the server. Old hashed assets accumulate slowly; that
    is a disk-space problem for later, and much safer than a delete that hits
    the wrong directory on a live site.

.PARAMETER FtpHost
.PARAMETER User
.PARAMETER RemoteDir
    Path as seen by this FTP account, e.g. public_html or /public_html.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\deploy_frontend_ftps.ps1
#>
[CmdletBinding()]
param(
    [string]$FtpHost   = '145.223.17.73',
    [string]$User      = 'u224349413',
    [int]$Port         = 21,
    [string]$RemoteDir = 'public_html',
    [string]$LocalDir  = '',
    [switch]$ListOnly
)

$ErrorActionPreference = 'Stop'
function Say  { param($m) Write-Host "==> $m" -ForegroundColor Cyan }
function Fail { param($m) Write-Host "ERROR: $m" -ForegroundColor Red; exit 1 }

$root = Split-Path -Parent $PSScriptRoot
if (-not $LocalDir) { $LocalDir = Join-Path $root 'frontend\dist' }
if (-not (Test-Path (Join-Path $LocalDir 'index.html'))) {
    Fail "No build at $LocalDir. Build first (see docs/DEPLOYMENT.md)."
}
if (-not (Test-Path (Join-Path $LocalDir '.htaccess'))) {
    Fail ".htaccess is missing from the build: every deep link (/shop, /product/...) would 404."
}

$secure = Read-Host -Prompt "FTP password for $User@$FtpHost" -AsSecureString
$cred = New-Object System.Net.NetworkCredential($User, $secure)

$base = "ftp://{0}:{1}/{2}" -f $FtpHost, $Port, $RemoteDir.Trim('/')

function New-Req { param([string]$Uri, [string]$Method)
    $r = [System.Net.FtpWebRequest]::Create($Uri)
    $r.Method = $Method
    $r.Credentials = $cred
    $r.EnableSsl = $true          # FTPS: never send credentials in clear text
    $r.UsePassive = $true
    $r.UseBinary = $true
    $r.KeepAlive = $true
    $r.Timeout = 120000
    return $r
}

# Hostinger presents a certificate for its own hostname, not the IP we connect
# to, so a strict name check fails. Accept it ONLY if the chain itself is valid
# and the sole problem is the name mismatch -- an untrusted or expired
# certificate is still refused.
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {
    param($sender, $cert, $chain, $errors)
    return ($errors -eq [System.Net.Security.SslPolicyErrors]::None) -or
           ($errors -eq [System.Net.Security.SslPolicyErrors]::RemoteCertificateNameMismatch)
}
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

# ── Connectivity + where we are ───────────────────────────────────────────
Say "Connecting (FTPS) to $FtpHost as $User"
try {
    $resp = (New-Req "$base/" ([System.Net.WebRequestMethods+Ftp]::ListDirectory)).GetResponse()
    $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
    $existing = $reader.ReadToEnd() -split "`r?`n" | Where-Object { $_ }
    $reader.Close(); $resp.Close()
} catch {
    Fail "Could not list $RemoteDir : $($_.Exception.InnerException.Message) $($_.Exception.Message)"
}
Write-Host "  remote $RemoteDir currently holds $($existing.Count) entr$(if ($existing.Count -eq 1) {'y'} else {'ies'})"
$existing | Select-Object -First 15 | ForEach-Object { Write-Host "    $_" }
if ($ListOnly) { Write-Host "  (list only: nothing uploaded)"; exit 0 }

# ── Build the upload list, index.html last ────────────────────────────────
$files = Get-ChildItem -Path $LocalDir -Recurse -File -Force |
    Where-Object { $_.Name -notlike '*.map' }
$index = $files | Where-Object { $_.FullName -eq (Join-Path $LocalDir 'index.html') }
$rest  = $files | Where-Object { $_.FullName -ne $index.FullName } | Sort-Object FullName
$ordered = @($rest) + @($index)

$createdDirs = @{}
function Ensure-Dir { param([string]$rel)
    if (-not $rel -or $createdDirs.ContainsKey($rel)) { return }
    $parts = $rel -split '/'
    $acc = ''
    foreach ($p in $parts) {
        $acc = if ($acc) { "$acc/$p" } else { $p }
        if ($createdDirs.ContainsKey($acc)) { continue }
        try { (New-Req "$base/$acc" ([System.Net.WebRequestMethods+Ftp]::MakeDirectory)).GetResponse().Close() }
        catch { }   # already exists
        $createdDirs[$acc] = $true
    }
}

Say "Uploading $($ordered.Count) files (index.html last)"
$bytes = 0
foreach ($f in $ordered) {
    $rel = $f.FullName.Substring($LocalDir.Length).TrimStart('\').Replace('\', '/')
    $dir = if ($rel.Contains('/')) { $rel.Substring(0, $rel.LastIndexOf('/')) } else { '' }
    Ensure-Dir $dir

    $req = New-Req "$base/$rel" ([System.Net.WebRequestMethods+Ftp]::UploadFile)
    $data = [System.IO.File]::ReadAllBytes($f.FullName)
    $req.ContentLength = $data.Length
    $stream = $req.GetRequestStream()
    $stream.Write($data, 0, $data.Length); $stream.Close()
    $req.GetResponse().Close()
    $bytes += $data.Length
    Write-Host ("  {0,8:N0} KB  {1}" -f ($data.Length / 1KB), $rel)
}

Write-Host ''
Write-Host ("SUCCESS: uploaded {0} files ({1:N1} MB) to {2}/{3}" -f $ordered.Count, ($bytes / 1MB), $FtpHost, $RemoteDir) -ForegroundColor Green
Write-Host 'Next: clear the Hostinger CDN cache (hPanel -> Dashboard -> Clear cache), or index.html may be served stale.'
