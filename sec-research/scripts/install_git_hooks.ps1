# install_git_hooks.ps1 — copy git hooks from sec-research/scripts/git-hooks/ into .git/hooks/.
#
# Run once after cloning the workspace, OR after pulling changes that update the
# hook scripts. The hooks are NOT auto-installed by git itself; this script does it.
#
# Existing .git/hooks/<name> files are backed up to .git/hooks/<name>.backup-<timestamp>.

$ErrorActionPreference = "Stop"

$workspaceRoot = git rev-parse --show-toplevel 2>$null
if (-not $workspaceRoot) {
    Write-Error "Not in a git repo."
    exit 1
}

$srcDir = Join-Path $workspaceRoot "sec-research\scripts\git-hooks"
$destDir = Join-Path $workspaceRoot ".git\hooks"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

if (-not (Test-Path $srcDir)) {
    Write-Error "Hook source dir not found: $srcDir"
    exit 1
}
if (-not (Test-Path $destDir)) {
    Write-Error "Git hooks dir not found: $destDir"
    exit 1
}

$hooks = @("pre-commit", "pre-push", "commit-msg")
foreach ($h in $hooks) {
    $src = Join-Path $srcDir $h
    $dest = Join-Path $destDir $h
    if (-not (Test-Path $src)) {
        Write-Warning "Hook source missing: $src"
        continue
    }
    if (Test-Path $dest) {
        $existing = Get-Content $dest -Raw
        $candidate = Get-Content $src -Raw
        if ($existing -eq $candidate) {
            Write-Host "[install_git_hooks] $h already up to date"
            continue
        }
        $backup = "$dest.backup-$timestamp"
        Move-Item $dest $backup
        Write-Host "[install_git_hooks] Backed up existing $h to $(Split-Path $backup -Leaf)"
    }
    Copy-Item $src $dest
    # Git hooks need to be executable. On Windows / Git for Windows, the file
    # extension and exec bit aren't always honored, but copying the content is
    # what matters; the shebang #!/bin/sh handles invocation.
    Write-Host "[install_git_hooks] Installed: $h"
}

Write-Host ""
Write-Host "Git hooks installed. They will fire on the next commit/push."
Write-Host "  G-1 (pre-commit)  : verify_finding on staged sec-research/findings/"
Write-Host "  G-2 (pre-commit)  : gitleaks-style secret scan (workspace-wide)"
Write-Host "  G-3 (pre-push)    : re-run G-1+G-2 on unpushed commits"
Write-Host "  G-4 (commit-msg)  : require Trace-ID: line when findings/ files staged"
Write-Host ""
Write-Host "To uninstall, remove the files from .git/hooks/."
