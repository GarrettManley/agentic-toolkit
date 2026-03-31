---
title: "Core Script: bootstrap_project.ps1"
date: 2026-03-30
draft: false
---

# Core Script: bootstrap_project.ps1

```text
# .ai/scripts/bootstrap_project.ps1
# Agentic Workspace - Project Injector (v1.0)
# Use: .\bootstrap_project.ps1 -TargetPath "C:\Path\To\New\Repo"

param (
    [Parameter(Mandatory=$true)]
    [string]$TargetPath
)

$workspaceRoot = "C:\Users\Garre\Workspace"
$templateSource = "$workspaceRoot\.ai\templates\project-init"
$globalSkills = "$workspaceRoot\.ai\skills"

Write-Host "🚀 Injecting Agentic Infrastructure into: $TargetPath" -ForegroundColor Cyan

# 1. Verification
if (!(Test-Path $TargetPath)) {
    Write-Error "❌ Target path not found: $TargetPath"
    exit 1
}

# 2. Create local .ai structure
$localAiPath = Join-Path $TargetPath ".ai"
if (!(Test-Path $localAiPath)) {
    New-Item -Path $localAiPath -ItemType Directory -Force
    Write-Host "✅ Created .ai/ directory." -ForegroundColor Gray
}

# 3. Inject Templates
Write-Host "📦 Copying context and ADR templates..." -ForegroundColor Gray
Copy-Item -Path "$templateSource\*" -Destination $localAiPath -Recurse -Force

# 4. Link Global Skills
# Instead of copying, we create a 'manifest' link to show it inherits from root
$manifest = @{
    project_name = (Split-Path $TargetPath -Leaf)
    parent_workspace = $workspaceRoot
    initialized_at = (Get-Date -Format 'yyyy-MM-dd')
    status = "Active"
} | ConvertTo-Json

Set-Content -Path (Join-Path $localAiPath "project-manifest.json") -Value $manifest

# 5. Summary
Write-Host "✨ Bootstrap Complete!" -ForegroundColor Green
Write-Host "The project is now 'Best-in-Class' Agentic compliant." -ForegroundColor Gray
Write-Host "Next Step: Task an agent to 'Audit this project using local truth-seeker skill'." -ForegroundColor Yellow

```

---
*Published from .ai active toolkit.*
