# Workspace Verification Script
$success = $true

Write-Host "--- Running Workspace Verification ---" -ForegroundColor Cyan

# 1. Verify GEMINI.md presence and standards
if (Test-Path "$PSScriptRoot\..\GEMINI.md") {
    Write-Host "[PASS] GEMINI.md exists." -ForegroundColor Green
} else {
    Write-Host "[FAIL] GEMINI.md missing." -ForegroundColor Red
    $success = $false
}

# 2. Verify Experiments Registry
$registry = Get-Content "$PSScriptRoot\..\.gemini\experiments.yaml"
if ($registry -match "Validated") {
    Write-Host "[PASS] Registry contains validated experiments." -ForegroundColor Green
} else {
    Write-Host "[FAIL] Registry seems empty or invalid." -ForegroundColor Red
    $success = $false
}

# 3. Verify Lab Website
if (Test-Path "$PSScriptRoot\..\site\hugo.toml") {
    Write-Host "[PASS] Lab website (Hugo) found." -ForegroundColor Green
} else {
    Write-Host "[FAIL] Lab website configuration missing." -ForegroundColor Red
    $success = $false
}

if ($success) {
    Write-Host "--- Verification Successful ---" -ForegroundColor Green
    exit 0
} else {
    Write-Host "--- Verification Failed ---" -ForegroundColor Red
    exit 1
}
