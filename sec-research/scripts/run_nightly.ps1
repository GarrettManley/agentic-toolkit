# run_nightly.ps1 — Windows Task Scheduler entry-point wrapper.
#
# Sets CWD to sec-research/, invokes nightly.py, captures exit code.
# Append the run record to runtime/scheduled-runs.jsonl regardless of success.
#
# Register via:
#   schtasks /Create /SC DAILY /ST 03:00 /TN "sec-research-nightly" `
#     /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\Garre\Workspace\sec-research\scripts\run_nightly.ps1"

$ErrorActionPreference = "Continue"
$workspaceRoot = Join-Path $PSScriptRoot ".." | Resolve-Path
Set-Location $workspaceRoot

$startedAt = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
Write-Host "[run_nightly.ps1] starting at $startedAt"

$python = "python"
# Watchdog: normal runs finish in ~1s; 2026-06-25 and 2026-07-03 hung 9-11 min
# and died with exit 99 and no inner run-record. Exit 98 = watchdog kill,
# distinct from 99 = failed to invoke.
$watchdogSeconds = 900
try {
    $proc = Start-Process -FilePath $python -ArgumentList "$workspaceRoot\scripts\nightly.py" `
        -WorkingDirectory $workspaceRoot -NoNewWindow -PassThru
    if ($proc.WaitForExit($watchdogSeconds * 1000)) {
        $exitCode = $proc.ExitCode
    } else {
        Write-Error "nightly.py exceeded ${watchdogSeconds}s watchdog; killing process tree (pid $($proc.Id))"
        taskkill /PID $proc.Id /T /F | Out-Null
        $exitCode = 98
    }
} catch {
    Write-Error "Failed to invoke nightly.py: $_"
    $exitCode = 99
}

$finishedAt = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
Write-Host "[run_nightly.ps1] finished at $finishedAt with exit $exitCode"

# Append run-record
$runRecord = @{
    kind         = "nightly-wrapper"
    started_at   = $startedAt
    finished_at  = $finishedAt
    exit_code    = $exitCode
    workspace    = $workspaceRoot.ToString()
} | ConvertTo-Json -Compress

$ledgerDir = Join-Path $workspaceRoot "runtime"
if (-not (Test-Path $ledgerDir)) { New-Item -ItemType Directory -Path $ledgerDir -Force | Out-Null }
$logFile = Join-Path $ledgerDir "scheduled-runs.jsonl"
Add-Content -Path $logFile -Value $runRecord

exit $exitCode
