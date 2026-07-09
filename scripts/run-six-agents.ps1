# Run all 6 specialist agents — CLI (default) or via live API (--Api).
param(
    [switch]$Api,
    [string]$Base = "http://127.0.0.1:8010",
    [switch]$DispatchSquads,
    [switch]$Refresh,
    [switch]$StartStack
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$env:ADVOI_FRAME_MOCK = "true"
$env:FIRSTMATE_FLEET_PATH = if ($env:FIRSTMATE_FLEET_PATH) { $env:FIRSTMATE_FLEET_PATH } else { "D:\Down\livekit-agent\deployment\firstmate-fleet" }

if ($StartStack) {
    & "$Root\scripts\run-multi-agent-stack.ps1"
}

if ($Api) {
    $qs = [System.Collections.Generic.List[string]]::new()
    if ($Refresh) { $qs.Add("refresh=true") }
    $qs.Add("confirmed=true")
    if ($DispatchSquads) { $qs.Add("dispatch_squads=true") }
    $url = "$Base/api/agents/run-six"
    if ($qs.Count -gt 0) { $url += "?" + ($qs -join "&") }
    Write-Host "==> POST $url"
    $data = Invoke-RestMethod -Uri $url -Method Post -ContentType "application/json" -Body "{}"
    Write-Host "agents_used: $($data.agents_used -join ', ')"
    Write-Host "spoken: $($data.spoken_summary.Substring(0, [Math]::Min(320, $data.spoken_summary.Length)))"
    if ($data.squads) {
        Write-Host "squads: $($data.squads.dispatched)/$($data.squads.total)"
    }
    exit 0
}

$mode = if ($DispatchSquads) { "six-squads" } else { "six" }
$args = @("run", "advoi-orchestrate", $mode)
if ($Refresh) { $args += "--refresh" }
uv @args