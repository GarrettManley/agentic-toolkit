---
title: "Core Script: verify_sync.ps1"
date: 2026-03-30
draft: false
---

# Core Script: verify_sync.ps1

```text
# .ai/scripts/verify_sync.ps1
# Truth-Validator: Ensures context is updated when code changes.

Write-Host "🛡️ Running Truth-Validator..." -ForegroundColor Cyan

# 1. Get staged files
$stagedFiles = git diff --cached --name-only

if ($stagedFiles.Count -eq 0) {
    Write-Host "✅ No staged files. Skipping check." -ForegroundColor Gray
    exit 0
}

$codeModified = $false
$contextUpdated = $false

foreach ($file in $stagedFiles) {
    if ($file -match "\.(cs|py|js|ts|dart)$") {
        $codeModified = $true
    }
    if ($file -match "\.ai/context/.*\.md$") {
        $contextUpdated = $true
    }
}

# 2. Enforcement Logic
if ($codeModified -and !$contextUpdated) {
    Write-Host "⚠️ DRIFT WARNING: You are committing code without updating the .ai/context Truth Files." -ForegroundColor Yellow
    Write-Host "Best-in-Class practice requires 'Context-Sync' for every code change." -ForegroundColor Gray
    
    # In a real hook, we might exit 1 to block the commit. 
    # For now, we log it.
    exit 0
}

Write-Host "✅ Sync verified. Proceeding with commit." -ForegroundColor Green
exit 0

```

---
*Published from .ai active toolkit.*
