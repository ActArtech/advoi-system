# Start ADVoi API only (PowerShell-safe; do not use bash && syntax).
param([int]$Port = 8010)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
if (-not (Test-Path deploy\.env)) { Copy-Item deploy\.env.local.example deploy\.env }
$env:ADVOI_FRAME_MOCK = "true"
$env:ADVOI_AGENT_INTERVAL_SECS = "30"
$env:ADVOI_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
$HealthUrl = "http://127.0.0.1:$Port/api/health"
try {
    $existing = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 2
    if ($existing.ok) {
        Write-Host "API already running on $HealthUrl (service=$($existing.service))"
        exit 0
    }
} catch {
    # port free or not our API
}

Write-Host "ADVoi API on http://127.0.0.1:$Port"
uv sync --quiet
uv run uvicorn advoi.api.app:app --host 127.0.0.1 --port $Port