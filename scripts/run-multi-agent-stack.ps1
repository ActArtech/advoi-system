# Clean start: Redis (optional) + API prewarm + 3-agent supervisor
param(
    [int]$ApiPort = 8010,
    [switch]$WithRedis,
    [switch]$WithWeb
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Test-Path deploy\.env)) {
    Copy-Item deploy\.env.local.example deploy\.env
}

$env:ADVOI_FRAME_MOCK = "true"
$env:ADVOI_AGENT_INTERVAL_SECS = "30"
$env:ADVOI_PREWARM_AGENTS = "true"
$env:ADVOI_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
$env:REDIS_URL = "redis://127.0.0.1:6382/0"

# Free API port
Get-NetTCPConnection -LocalPort $ApiPort -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

if ($WithRedis) {
    docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        docker compose --env-file deploy/.env up -d redis 2>&1 | Out-Host
        Start-Sleep -Seconds 3
        uv run python scripts/seed-local-briefs.py 2>&1 | Out-Host
    } else {
        Write-Host "WARN: Docker not running, continuing without Redis cache"
    }
}

Write-Host "==> Starting API :$ApiPort (prewarm on startup)"
$apiProc = Start-Process -PassThru -WindowStyle Hidden -FilePath "uv" `
    -ArgumentList "run","uvicorn","advoi.api.app:app","--host","127.0.0.1","--port",$ApiPort `
    -WorkingDirectory $Root

Start-Sleep -Seconds 4

Write-Host "==> Starting 3-agent supervisor (fleet, briefs, review)"
$agentProc = Start-Process -PassThru -WindowStyle Hidden -FilePath "uv" `
    -ArgumentList "run","python","-m","advoi.routing.agent_supervisor" `
    -WorkingDirectory $Root

if ($WithWeb) {
    Write-Host "==> Starting Next.js dev"
    $webProc = Start-Process -PassThru -WindowStyle Hidden -FilePath "npm" `
        -ArgumentList "run","dev" -WorkingDirectory (Join-Path $Root "web")
}

Start-Sleep -Seconds 3
.\scripts\agents-smoke-test.ps1 -Base "http://127.0.0.1:$ApiPort"

try {
    $diag = Invoke-RestMethod "http://127.0.0.1:$ApiPort/api/diagnostics/agents"
    Write-Host "Agents ready: $($diag.ready)/$($diag.total) redis=$($diag.redis)"
} catch {
    Write-Host "WARN: diagnostics/agents failed"
}

Write-Host ""
Write-Host "Stack running:"
Write-Host "  API     PID $($apiProc.Id)  http://127.0.0.1:$ApiPort"
Write-Host "  Agents  PID $($agentProc.Id)"
if ($WithWeb) { Write-Host "  Web     PID $($webProc.Id)  http://localhost:3000" }
Write-Host "Stop: Stop-Process -Id $($apiProc.Id),$($agentProc.Id) -Force"