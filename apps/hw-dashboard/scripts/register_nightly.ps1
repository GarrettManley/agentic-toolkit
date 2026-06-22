# register_nightly.ps1 — register the nightly price collector with Task Scheduler.
#
# Daily at 03:15 LOCAL time. The machine is on Mountain Time (America/Denver), and
# Task Scheduler triggers fire in local time and auto-handle DST, so a local 03:15
# trigger IS 03:15 MT. -StartWhenAvailable catches missed runs after sleep; the
# collector's idempotent append makes a catch-up run a safe no-op.
#
# Usage:  pwsh -NoProfile -File scripts/register_nightly.ps1 [-At 03:15] [-Unregister]

[CmdletBinding()]
param(
    [string]$At = "03:15",
    [string]$TaskName = "hw-dashboard-nightly",
    [switch]$Unregister
)
$ErrorActionPreference = "Stop"

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "[register_nightly] unregistered '$TaskName'"
    return
}

$tz = (tzutil /g)
if ($tz -notmatch "Mountain") {
    Write-Warning "System time zone is '$tz', not Mountain. The 03:15 trigger fires in LOCAL time."
}

$wrapper = Join-Path $PSScriptRoot "run_nightly.ps1" | Resolve-Path
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$wrapper`""
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Nightly PC-hardware price snapshot collector" -Force | Out-Null

Write-Host "[register_nightly] registered '$TaskName' daily at $At local time"
Write-Host "  wrapper: $wrapper"
Write-Host "  remove with: pwsh -File scripts/register_nightly.ps1 -Unregister"
