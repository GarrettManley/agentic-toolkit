param (
    [switch]$List,
    [switch]$Summary
)

$yamlPath = Join-Path $PSScriptRoot "..\.gemini\experiments.yaml"

if (-not (Test-Path $yamlPath)) {
    Write-Error "Experiments registry not found at $yamlPath"
    exit 1
}

# Super simple parsing for demo purposes (assuming no complex nesting in the yaml)
$yamlContent = Get-Content $yamlPath

if ($List) {
    Write-Host "--- Agentic Workspace Experiments ---" -ForegroundColor Cyan
    $currentId = ""
    $currentName = ""
    $currentStatus = ""
    
    foreach ($line in $yamlContent) {
        if ($line -match 'id:\s*"([^"]+)"') { $currentId = $matches[1] }
        if ($line -match 'name:\s*"([^"]+)"') { $currentName = $matches[1] }
        if ($line -match 'status:\s*"([^"]+)"') { 
            $currentStatus = $matches[1] 
            
            $color = "White"
            if ($currentStatus -eq "Validated") { $color = "Green" }
            elseif ($currentStatus -eq "Rejected") { $color = "Red" }
            elseif ($currentStatus -eq "Running") { $color = "Yellow" }
            
            Write-Host "[$currentId] $currentName - Status: $currentStatus" -ForegroundColor $color
        }
    }
}
elseif ($Summary) {
    $validatedCount = ($yamlContent | Select-String 'status:\s*"Validated"').Count
    $totalCount = ($yamlContent | Select-String 'id:\s*".*"').Count
    Write-Host "Total Experiments: $totalCount"
    Write-Host "Validated: $validatedCount" -ForegroundColor Green
}
else {
    Write-Host "Usage: .\manage_experiments.ps1 -List | -Summary"
}
