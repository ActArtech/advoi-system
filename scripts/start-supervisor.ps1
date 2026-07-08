# Start 3-agent supervisor only (PowerShell-safe; do not use bash && syntax).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$env:ADVOI_FRAME_MOCK = "true"
$env:ADVOI_AGENT_INTERVAL_SECS = "30"
Write-Host "ADVoi supervisor: fleet-scout, brief-curator, review-queue"
uv sync --quiet
uv run advoi-supervisor