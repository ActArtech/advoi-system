param([string]$Base = "https://advoi.keyteller.com")
$fail = 0
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> ADVoi staging sign-off pre-check"
Write-Host "    Base URL: $Base"
Write-Host ""

function Run-Step($name, $script) {
    Write-Host "==> $name"
    try {
        & $script
        if ($LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE" }
        Write-Host "    OK"
    } catch {
        Write-Host "    FAIL"
        $script:fail = 1
    }
    Write-Host ""
}

Run-Step "voice-smoke-test" { $env:ADVOI_BASE_URL = $Base; bash scripts/voice-smoke-test.sh }

Write-Host "==> latency diagnostics"
try {
    $lat = Invoke-RestMethod -Uri "$Base/api/diagnostics/latency"
    $t = $lat.timings_ms
    Write-Host "    health_ms=$($t.health_ms) frame_run_ms=$($t.frame_run_ms) api_voice_path_ms=$($t.api_voice_path_ms)"
    Write-Host "    sla_target_ms=$($lat.sla_target_ms) sla_ok=$($lat.sla_ok)"
    if (-not $lat.ok) { $fail = 1; Write-Host "    FAIL (ok=false)" } else { Write-Host "    OK" }
} catch { Write-Host "    FAIL"; $fail = 1 }
Write-Host ""

Write-Host "==> agents cache"
try {
    $agents = Invoke-RestMethod -Uri "$Base/api/agents"
    Write-Host "    $($agents.ready)/$($agents.total) ready"
    if ($agents.ready -lt 3) { $fail = 1; Write-Host "    FAIL" } else { Write-Host "    OK" }
} catch { Write-Host "    FAIL"; $fail = 1 }
Write-Host ""

if ($fail -eq 0) {
    Write-Host "=========================================="
    Write-Host "AUTOMATED PRE-CHECKS PASSED"
    Write-Host "Next: human E2E (docs/operations/E2E-SIGNOFF.md)"
    Write-Host "=========================================="
    exit 0
}
Write-Host "PRE-CHECKS FAILED"
exit 1