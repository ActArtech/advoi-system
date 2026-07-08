param([int]$ApiPort = 8010)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
if (-not (Test-Path deploy\.env)) { Copy-Item deploy\.env.local.example deploy\.env }
$env:ADVOI_FRAME_MOCK = "true"
$env:ADVOI_AGENT_INTERVAL_SECS = "30"
$env:ADVOI_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
uv sync --quiet
Write-Host "Starting API on :$ApiPort"
Start-Process -NoNewWindow -FilePath "uv" -ArgumentList "run","uvicorn","advoi.api.app:app","--host","127.0.0.1","--port",$ApiPort -WorkingDirectory $Root
Start-Sleep -Seconds 3
Write-Host "Starting agent supervisor (3 specialists)"
Start-Process -NoNewWindow -FilePath "uv" -ArgumentList "run","advoi-supervisor" -WorkingDirectory $Root -Environment @{ ADVOI_FRAME_MOCK="true"; ADVOI_AGENT_INTERVAL_SECS="30" }
Start-Sleep -Seconds 3
Invoke-WebRequest -Uri "http://127.0.0.1:$ApiPort/api/health" -UseBasicParsing | Out-Null
Write-Host "OK: API + 3 agents running (mock mode)"
Write-Host "Test: curl http://127.0.0.1:$ApiPort/api/agents"