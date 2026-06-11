# Pre-commit Audit Tool
#
# Scans source Markdown for un-finalized placeholders (literal "TBD") and walks YAML
# for obvious breakage, before work is declared complete (GEMINI.md §3). Exit 0 = clean,
# exit 1 = findings — consumed both manually and by the commit-time verify gate
# (.claude/hooks/check_verify_before_commit.py).
#
# Performance: an explicit prune walk descends the tree but NEVER enters the heavy /
# vendored directories below. The previous `Get-ChildItem -Recurse` walked
# node_modules + site/themes before path-filtering (~20s, which tripped the gate's
# timeout and made it fail open); pruning at descent brings it to ~1-2s.
#
# Pruned (never descended):
#   node_modules, themes, public, dist, .git, *cache, .firebase  - vendored / generated / VCS
#   Duracell*, malachite                                         - isolated corporate repos (NEVER scan - GEMINI.md §4)
#   System.Control, Roleplaying                                  - nested independent repos with their own gates
#   archetypes, .gemini, superpowers, .superpowers, retrospectives - spec/plan/scaffold/retro trees whose "TBD" markers are intentional or quoted narrative

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path "$PSScriptRoot\..").Path
$errorCount = 0

# A path segment is pruned if it matches one of these names. Anchored on path
# separators so it matches whole directory names, not substrings.
$prunePattern = '[\\/](node_modules|themes|public|dist|\.git|\.ruff_cache|\.pytest_cache|\.firebase|\.superpowers|Duracell[^\\/]*|malachite|System\.Control|Roleplaying|archetypes|\.gemini|superpowers|retrospectives)([\\/]|$)'

function Get-AuditFiles {
    param([string]$Root, [string]$Prune, [string[]]$Extensions)
    $results = [System.Collections.Generic.List[string]]::new()
    $stack = [System.Collections.Generic.Stack[string]]::new()
    $stack.Push($Root)
    while ($stack.Count -gt 0) {
        $dir = $stack.Pop()
        try { $entries = [System.IO.Directory]::EnumerateFileSystemEntries($dir) }
        catch { continue }  # unreadable dir — skip, don't abort the audit
        foreach ($entry in $entries) {
            if ([System.IO.Directory]::Exists($entry)) {
                if ($entry -notmatch $Prune) { $stack.Push($entry) }
            } else {
                foreach ($ext in $Extensions) {
                    if ($entry.EndsWith($ext, [System.StringComparison]::OrdinalIgnoreCase)) {
                        $results.Add($entry); break
                    }
                }
            }
        }
    }
    return $results
}

# 1. Hardcoded TBD placeholders in Markdown.
foreach ($file in (Get-AuditFiles -Root $root -Prune $prunePattern -Extensions '.md')) {
    if (Select-String -LiteralPath $file -Pattern 'TBD' -Quiet) {
        Write-Host "[FAIL] Hardcoded TBD found in $(Split-Path $file -Leaf)" -ForegroundColor Red
        $errorCount++
    }
}

# 2. YAML sanity — flag files that fail to read as text (lenient, matches prior intent).
foreach ($file in (Get-AuditFiles -Root $root -Prune $prunePattern -Extensions @('.yaml', '.yml'))) {
    try { $null = Get-Content -LiteralPath $file -ErrorAction Stop }
    catch {
        Write-Host "[FAIL] Could not read YAML $(Split-Path $file -Leaf)" -ForegroundColor Red
        $errorCount++
    }
}

if ($errorCount -eq 0) {
    Write-Host "[PASS] Pre-commit audit successful." -ForegroundColor Green
    exit 0
} else {
    Write-Host "[FAIL] Pre-commit audit failed with $errorCount errors." -ForegroundColor Red
    exit 1
}
