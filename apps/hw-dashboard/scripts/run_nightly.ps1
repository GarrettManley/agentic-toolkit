# run_nightly.ps1 — Windows Task Scheduler entry-point wrapper for the price collector.
#
# Sets CWD to apps/hw-dashboard/, invokes the collector via uv (reproducible env),
# captures the exit code, and appends a wrapper run-record to data/collector-runs.jsonl
# regardless of success. Register with scripts/register_nightly.ps1.

$ErrorActionPreference = "Continue"
$appRoot = Join-Path $PSScriptRoot ".." | Resolve-Path
Set-Location $appRoot

$startedAt = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
Write-Host "[run_nightly] starting at $startedAt"

try {
    # Prefer uv (pinned env); fall back to bare python if uv is unavailable.
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        & uv run python -m collector.collect
    } else {
        & python -m collector.collect
    }
    $exitCode = $LASTEXITCODE
} catch {
    Write-Error "Failed to invoke collector: $_"
    $exitCode = 99
}

$finishedAt = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
Write-Host "[run_nightly] finished at $finishedAt with exit $exitCode"

$runRecord = @{
    kind        = "nightly-wrapper"
    started_at  = $startedAt
    finished_at = $finishedAt
    exit_code   = $exitCode
    app_root    = $appRoot.ToString()
} | ConvertTo-Json -Compress

$logFile = Join-Path $appRoot "data\collector-runs.jsonl"
$logDir = Split-Path -Parent $logFile
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
Add-Content -Path $logFile -Value $runRecord

exit $exitCode
