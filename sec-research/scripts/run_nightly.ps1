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
try {
    & $python "$workspaceRoot\scripts\nightly.py"
    $exitCode = $LASTEXITCODE
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
