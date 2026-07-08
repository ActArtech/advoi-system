# Create deploy/.env from local example (PowerShell-safe).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Src = Join-Path $Root "deploy\.env.local.example"
$Dest = Join-Path $Root "deploy\.env"
if (-not (Test-Path $Src)) { throw "Missing $Src" }
if (Test-Path $Dest) {
    Write-Host "deploy/.env already exists"
    exit 0
}
Copy-Item $Src $Dest
Write-Host "OK: created deploy/.env"