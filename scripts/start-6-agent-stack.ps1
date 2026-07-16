# Lean 6-agent stack — uses venv python directly (avoids uv lock on Windows).
param([int]$ApiPort = 8014)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

& (Join-Path $Root "scripts\stop-advoi-agents.ps1")
Start-Sleep -Seconds 2

$py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Missing $py — run uv sync first" }

$env:ADVOI_FRAME_MOCK = "true"
$env:ADVOI_AGENT_INTERVAL_SECS = "30"
$env:ADVOI_PREWARM_AGENTS = "true"
$env:ADVOI_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
$env:OTEL_ENABLED = "false"

Get-NetTCPConnection -LocalPort $ApiPort -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

Write-Host "==> API :$ApiPort"
$apiProc = Start-Process -PassThru -WindowStyle Hidden -FilePath $py `
    -ArgumentList "-m","uvicorn","advoi.api.app:app","--host","127.0.0.1","--port",$ApiPort `
    -WorkingDirectory $Root

Start-Sleep -Seconds 5

Write-Host "==> 6-agent supervisor"
$agentProc = Start-Process -PassThru -WindowStyle Hidden -FilePath $py `
    -ArgumentList "-m","advoi.routing.agent_supervisor" `
    -WorkingDirectory $Root

Start-Sleep -Seconds 8

Write-Host "==> Health"
$health = Invoke-RestMethod "http://127.0.0.1:$ApiPort/api/health"
Write-Host ($health | ConvertTo-Json -Compress)

Write-Host "==> Run-six"
$run = Invoke-RestMethod -Method Post "http://127.0.0.1:$ApiPort/api/agents/run-six?refresh=true&confirmed=true"
Write-Host "frames: $($run.results.Count) agents: $($run.agents_used -join ', ')"

Write-Host ""
Write-Host "Running:"
Write-Host "  API     PID $($apiProc.Id)  http://127.0.0.1:$ApiPort"
Write-Host "  Agents  PID $($agentProc.Id)"
Write-Host "Stop: Stop-Process -Id $($apiProc.Id),$($agentProc.Id) -Force"