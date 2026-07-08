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
Check-Post "voice respond" "$Base/api/voice/respond" '{"transcript":"What briefs are open?"}' "spoken"
Check-Get "frame intents" "$Base/api/frames" "voice_prompt"
Check-Get "review queue" "$Base/api/review-queue" "pending"
foreach ($id in @("fleet_status", "open_briefs", "queue_deep_review")) {
    Write-Host -NoNewline "==> intent $id ... "
    try {
        $frames = (Invoke-RestMethod -Uri "$Base/api/frames").frames
        $frame = $frames | Where-Object { $_.id -eq $id }
        if ($frame -and $frame.voice_prompt) { Write-Host "OK" }
        else { Write-Host "FAIL"; $fail = 1 }
    } catch { Write-Host "FAIL"; $fail = 1 }
}
$agents = Invoke-RestMethod -Uri "$Base/api/agents"
foreach ($id in @("fleet-scout","brief-curator","review-queue")) {
    Write-Host -NoNewline "==> agent $id ... "
    $a = $agents.agents | Where-Object { $_.id -eq $id }
    if ($a) { Write-Host "OK" } else { Write-Host "FAIL"; $fail = 1 }
}
Write-Host -NoNewline "==> diagnostics/agents ... "
try {
    $d = Invoke-RestMethod -Uri "$Base/api/diagnostics/agents"
    if ($d.total -eq 3) { Write-Host "OK ($($d.ready)/$($d.total) cached)" } else { Write-Host "FAIL"; $fail = 1 }
} catch { Write-Host "FAIL"; $fail = 1 }
Write-Host -NoNewline "==> agent last_run ... "
try {
    $cached = ($agents.agents | Where-Object { $_.last_run }).Count
    if ($cached -gt 0) { Write-Host "OK ($cached/3 cached)" }
    else { Write-Host "WARN (no cache yet)" }
} catch { Write-Host "FAIL"; $fail = 1 }
if ($fail -eq 0) { Write-Host "All passed."; exit 0 }
Write-Host "Some failed."; exit 1