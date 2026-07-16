# Stop stray ADVoi python/node processes (Windows dev hygiene).
param([switch]$Force)

Write-Host "Stopping ADVoi-related processes..."
$names = @("python", "pythonw")
foreach ($n in $names) {
    Get-Process -Name $n -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine
            if ($cmd -match "advoi|uvicorn|agent_supervisor|advoi-supervisor") {
                Write-Host "  kill PID $($_.Id): $($cmd.Substring(0, [Math]::Min(80, $cmd.Length)))"
                Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
            }
        } catch { }
    }
}
Write-Host "Done. Restart with: .\scripts\start-6-agent-stack.ps1 -ApiPort 8014"