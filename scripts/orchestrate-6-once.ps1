# One-shot: run all 6 agent frames in parallel (no long-running daemons).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$env:ADVOI_FRAME_MOCK = "true"
$py = Join-Path $Root ".venv\Scripts\python.exe"
& $py -m advoi.routing.orchestrate_cli json --refresh