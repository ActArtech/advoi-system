# Preload staging for human Path A E2E (runs preload on VPS + local precheck).
param(
    [string]$Base = "https://advoi.keyteller.com",
    [string]$VpsHost = "deploy@187.77.140.216",
    [switch]$SkipPrecheck
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> ADVoi E2E preload (VPS + verify)"
Write-Host "    Base URL: $Base"
Write-Host ""

Write-Host "==> Run preload on VPS (/opt/advoi)"
ssh $VpsHost "cd /opt/advoi && sed -i 's/\r$//' scripts/preload-staging-e2e.sh 2>/dev/null; ADVOI_BASE_URL=$Base bash scripts/preload-staging-e2e.sh"
Write-Host ""

if (-not $SkipPrecheck) {
    Write-Host "==> Automated precheck"
    $env:ADVOI_BASE_URL = $Base
    & "$Root\scripts\staging-signoff-precheck.ps1" -Base $Base
}