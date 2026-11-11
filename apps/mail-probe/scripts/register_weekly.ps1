# register_weekly.ps1 — register the jobs@ delivery probe with Task Scheduler.
#
# Mondays at 07:00 LOCAL time (machine is America/Denver; triggers fire in local time and
# follow DST). -StartWhenAvailable catches a missed run after sleep/shutdown. Runs as the
# current user, interactive-only, because the secrets live in this user's Credential Manager.
#
# Usage:  pwsh -NoProfile -File scripts/register_weekly.ps1 [-At 07:00] [-Day Monday] [-Unregister]

[CmdletBinding()]
param(
    [string]$At = "07:00",
    [System.DayOfWeek]$Day = [System.DayOfWeek]::Monday,
    [string]$TaskName = "mail-probe-weekly",
    [switch]$Unregister
)
$ErrorActionPreference = "Stop"

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "[register_weekly] unregistered '$TaskName'"
    return
}

$wrapper = Join-Path $PSScriptRoot "run_weekly.ps1" | Resolve-Path
$action = New-ScheduledTaskAction -Execute "pwsh.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$wrapper`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Day -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable `
    -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Weekly end-to-end delivery probe for jobs@garrettmanley.dev (apps/mail-probe)" -Force | Out-Null

Write-Host "[register_weekly] registered '$TaskName' every $Day at $At local time"
Write-Host "  wrapper: $wrapper"
