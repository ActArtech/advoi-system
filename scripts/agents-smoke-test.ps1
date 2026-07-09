param([string]$Base = "http://127.0.0.1:8010")
$fail = 0
function Check-Post($name, $url, $body = "{}", $expect = $null) {
    Write-Host -NoNewline "==> $name ... "
    try {
        $resp = Invoke-RestMethod -Uri $url -Method Post -ContentType "application/json" -Body $body
        if ($expect -and ($resp | ConvertTo-Json -Compress) -notmatch [regex]::Escape($expect)) {
            Write-Host "FAIL (missing $expect)"; $script:fail = 1; return
        }
        Write-Host "OK"
    } catch { Write-Host "FAIL"; $script:fail = 1 }
}
function Check-Get($name, $url, $expect) {
    Write-Host -NoNewline "==> $name ... "
    try {
        $resp = Invoke-RestMethod -Uri $url
        $json = $resp | ConvertTo-Json -Compress
        if ($json -match [regex]::Escape($expect)) { Write-Host "OK" }
        else { Write-Host "FAIL (missing $expect)"; $script:fail = 1 }
    } catch { Write-Host "FAIL"; $script:fail = 1 }
}
Write-Host "==> Multi-agent smoke ($Base)"
try { Invoke-RestMethod -Uri "$Base/api/health" | Out-Null; Write-Host "OK: health" }
catch { Write-Host "FAIL: API down"; exit 1 }
Check-Post "fleet" "$Base/api/frames/fleet_status/run"
Check-Post "briefs" "$Base/api/frames/open_briefs/run"
Check-Post "review" "$Base/api/frames/queue_deep_review/run" '{"confirmed":true}'
Check-Post "systems pulse" "$Base/api/frames/systems_pulse/run"
Check-Post "memory health" "$Base/api/frames/memory_health/run"
Check-Post "guardian status" "$Base/api/frames/guardian_status/run"
Check-Post "run all agents" "$Base/api/agents/run-all?refresh=true&confirmed=true" "{}" "systems_pulse"
Check-Post "run six agents" "$Base/api/agents/run-six?refresh=true&confirmed=true" "{}" "guardian_status"
Check-Get "squads" "$Base/api/squads" "fleet-squad"
Check-Get "platform diagnostics" "$Base/api/diagnostics/platform" "multi_agent"
Check-Post "voice respond" "$Base/api/voice/respond" '{"transcript":"systems pulse"}' "spoken"
Write-Host -NoNewline "==> voice speak (validation) ... "
try {
    $r = Invoke-WebRequest -Uri "$Base/api/voice/speak" -Method Post -ContentType "application/json" -Body '{"text":"  "}' -SkipHttpErrorCheck
    if ($r.StatusCode -eq 400) { Write-Host "OK" } else { Write-Host "FAIL (expected 400)"; $fail = 1 }
} catch { Write-Host "FAIL"; $fail = 1 }
Check-Get "frame intents" "$Base/api/frames" "guardian_status"
Check-Get "review queue" "$Base/api/review-queue" "pending"
Check-Get "guardian" "$Base/api/diagnostics/guardian" "confirmation_enabled"
Check-Get "memory diagnostics" "$Base/api/diagnostics/memory" "operational_store_enabled"
foreach ($id in @("fleet-scout","brief-curator","review-queue","systems-pulse","memory-scout","guardian-sentinel")) {
    Write-Host -NoNewline "==> agent $id ... "
    $a = (Invoke-RestMethod -Uri "$Base/api/agents").agents | Where-Object { $_.id -eq $id }
    if ($a) { Write-Host "OK" } else { Write-Host "FAIL"; $fail = 1 }
}
Write-Host -NoNewline "==> diagnostics/agents ... "
try {
    $d = Invoke-RestMethod -Uri "$Base/api/diagnostics/agents"
    if ($d.total -eq 6) { Write-Host "OK ($($d.ready)/$($d.total) cached)" } else { Write-Host "FAIL (total=$($d.total))"; $fail = 1 }
} catch { Write-Host "FAIL"; $fail = 1 }
if ($fail -eq 0) { Write-Host "All passed."; exit 0 }
Write-Host "Some failed."; exit 1