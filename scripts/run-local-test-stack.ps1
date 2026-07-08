param([switch]$Build, [switch]$NoVoice, [switch]$NoWeb)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
if (-not (Test-Path deploy\.env)) { Copy-Item deploy\.env.local.example deploy\.env }
docker info *> $null
if ($LASTEXITCODE -ne 0) { Write-Host "Start Docker Desktop first, or use run-agents-uv.ps1"; exit 1 }
$services = @("postgres","redis","advoi-memory-bridge","advoi-api","advoi-agent-fleet","advoi-agent-briefs","advoi-agent-review","livekit")
if (-not $NoVoice) { $services += "advoi-voice" }
if (-not $NoWeb) { $services += "advoi-web" }
$args = @("compose","--profile","app","--env-file","deploy/.env","up","-d")
if ($Build) { $args += "--build" }
$args += $services
docker @args
$apiPort = if ($env:ADVOI_API_PORT) { $env:ADVOI_API_PORT } else { "8010" }
Start-Sleep -Seconds 8
$env:ADVOI_BASE_URL = "http://127.0.0.1:$apiPort"
bash scripts/agents-smoke-test.sh
Write-Host "Ready: http://127.0.0.1:$apiPort/api/agents"