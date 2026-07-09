# Run all 6 specialist agents in parallel (no HTTP server required)
param(
    [ValidateSet("prewarm", "parallel", "pulse", "six", "six-squads", "all", "json")]
    [string]$Mode = "all",
    [switch]$Refresh,
    [switch]$DispatchSquads
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$env:ADVOI_FRAME_MOCK = "true"
$args = @("run", "advoi-orchestrate", $Mode)
if ($Refresh) { $args += "--refresh" }
if ($DispatchSquads) { $args += "--dispatch-squads" }
uv @args