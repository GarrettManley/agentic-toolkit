# run_weekly.ps1 — Task Scheduler entry point for the jobs@ delivery probe.
#
# Sets CWD to apps/mail-probe/, runs the probe via uv, and pops a Windows toast on any
# non-zero exit (the probe itself writes the healthcheck JSON + runs.jsonl and sends the
# alert email). Register with scripts/register_weekly.ps1.

$ErrorActionPreference = "Continue"
$appRoot = Join-Path $PSScriptRoot ".." | Resolve-Path
Set-Location $appRoot

try {
    # Secrets come from 1Password (.env.tpl refs) via the read-only service account whose
    # token lives in Credential Manager — see ~/scripts/lib/Secrets.psm1.
    Import-Module (Join-Path $HOME 'scripts\lib\Secrets.psm1') -Force
    Invoke-WithSecrets -ServiceAccount -EnvFile (Join-Path $appRoot '.env.tpl') -- `
        uv run --no-dev python -m mail_probe.probe @args
    $exitCode = $LASTEXITCODE
} catch {
    Write-Error "Failed to invoke probe: $_"
    $exitCode = 99
}

if ($exitCode -ne 0) {
    $title = "mail-probe FAILED (exit $exitCode)"
    $body = "jobs@garrettmanley.dev check failed. See ~/.claude/stewardship/healthchecks/mail-probe.json"
    if (Get-Command New-BurntToastNotification -ErrorAction SilentlyContinue) {
        New-BurntToastNotification -Text $title, $body
    } else {
        Add-Type -AssemblyName System.Windows.Forms
        $n = New-Object System.Windows.Forms.NotifyIcon
        $n.Icon = [System.Drawing.SystemIcons]::Warning
        $n.Visible = $true
        $n.ShowBalloonTip(30000, $title, $body, [System.Windows.Forms.ToolTipIcon]::Error)
        Start-Sleep -Seconds 10   # keep the process alive long enough for the balloon to render
        $n.Dispose()
    }
}

exit $exitCode
