---
title: "Core Script: steward.ps1"
date: 2026-03-30
draft: false
---

# Core Script: steward.ps1

```text
# .ai/scripts/steward.ps1
# Nightly Steward - Workspace Maintenance & Audit Script (v1.0)

$workspaceRoot = "C:\Users\Garre\Workspace"
$contextDir = "$workspaceRoot\.ai\context"
$templatePath = "$workspaceRoot\.ai\templates\morning-briefing.md"
$briefingPath = "$workspaceRoot\docs\superpowers\maintenance\$(Get-Date -Format 'yyyy-MM-dd')-briefing.md"

# Ensure output directory exists
if (!(Test-Path "$workspaceRoot\docs\superpowers\maintenance")) {
    New-Item -Path "$workspaceRoot\docs\superpowers\maintenance" -ItemType Directory -Force
}

Write-Host "🚀 Starting Nightly Steward Audit..." -ForegroundColor Cyan

$verifiedFiles = @()
$drifts = @()

# 1. Perform Drift Check
$files = Get-ChildItem -Path $contextDir -Filter *.md -Recurse
foreach ($file in $files) {
    $content = Get-Content $file.FullName -Raw
    
    # Extract verification_cmd using regex
    if ($content -match 'verification_cmd:\s*"(.*)"') {
        $cmd = $Matches[1]
        Write-Host "🔍 Verifying: $($file.Name) -> $cmd" -ForegroundColor Gray
        
        try {
            # Execute command and capture output
            $result = Invoke-Expression $cmd
            $verifiedFiles += "- [x] $($file.Name): Verified successfully."
        } catch {
            Write-Host "⚠️ Drift detected in $($file.Name)" -ForegroundColor Yellow
            $drifts += @{
                file = $file.Name
                issue = "Verification command failed: $($_.Exception.Message)"
                fix = "Manual review required to update Truth File or fix code."
            }
        }
    }
}

# 2. Horizon Scan Placeholder
$discoveries = "- [ ] Searching for new models..."

# 3. Generate Morning Briefing
if (Test-Path $templatePath) {
    $briefingContent = Get-Content $templatePath -Raw
    $briefingContent = $briefingContent -replace '\{\{DATE\}\}', (Get-Date -Format 'yyyy-MM-dd HH:mm')
    $briefingContent = $briefingContent -replace '\{\{AUDIT_STATUS\}\}', (if ($drifts.Count -eq 0) { "✅ PASS" } else { "⚠️ DRIFT" })

    $verifiedString = if ($verifiedFiles.Count -gt 0) { $verifiedFiles -join "`n" } else { "No files verified." }
    $briefingContent = $briefingContent -replace '- \[ \] \{\{FILE_NAME\}\}: \{\{SUMMARY_OF_CHANGE\}\}', $verifiedString

    $driftString = ""
    if ($drifts.Count -gt 0) {
        foreach ($d in $drifts) {
            $driftString += "- **Issue**: $($d.issue)`n  - **Source**: $($d.file)`n  - **Proposed Fix**: $($d.fix)`n`n"
        }
    } else {
        $driftString = "No drift detected."
    }
    $briefingContent = $briefingContent -replace '- \*\*Issue\*\*: \{\{DRIFT_DESCRIPTION\}\}\n- \*\*Source\*\*: \{\{FILE_PATH\}\}\n- \*\*Proposed Fix\*\*: \{\{FIX_PLAN\}\}', $driftString

    Set-Content -Path $briefingPath -Value $briefingContent
    Write-Host "✅ Audit complete. Morning Briefing generated at $briefingPath" -ForegroundColor Green
} else {
    Write-Host "❌ Error: Template not found at $templatePath" -ForegroundColor Red
}

```

---
*Published from .ai active toolkit.*
