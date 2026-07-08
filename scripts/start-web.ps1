# Start Next.js dev server (PowerShell-safe).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Web = Join-Path $Root "web"
Set-Location $Web

try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:3000" -UseBasicParsing -TimeoutSec 2
    if ($resp.StatusCode -eq 200) {
        Write-Host "Web already running at http://localhost:3000"
        exit 0
    }
} catch {
    # not running
}

if (-not (Test-Path node_modules)) {
    Write-Host "Installing npm dependencies..."
    npm install
}

Write-Host "ADVoi web dev server at http://localhost:3000"
npm run dev