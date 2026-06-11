# publish.ps1
# Agentic Workspace - Local CI/CD Orchestrator (v1.1)
# Use: .\publish.ps1

# Skip-publish guard: if the most recent commit only changed sec-research/ paths,
# skip the entire pipeline. sec-research/ is operational data (findings, programs,
# evidence) — NOT documentation to publish. Avoids unnecessary Firebase redeploys
# and provides defense-in-depth against accidentally publishing undisclosed findings.
$changed = git diff --name-only HEAD~1 HEAD 2>$null
if ($LASTEXITCODE -eq 0 -and $changed) {
    $allSecResearch = $true
    foreach ($file in $changed) {
        if ($file -and -not $file.StartsWith("sec-research/")) {
            $allSecResearch = $false
            break
        }
    }
    if ($allSecResearch) {
        Write-Host "Skip-publish guard: commit only touched sec-research/. No publish needed." -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "Initializing Local CI/CD Pipeline..." -ForegroundColor Cyan

# Force Python UTF-8 mode for all child processes. The toolkit/spec generators
# print emoji status lines; Windows' default cp1252 stdout raises UnicodeEncodeError
# on them, which previously left publish_toolkit.py / generate_spec.py partially run
# (the toolkit dir got wiped but not fully regenerated). UTF-8 mode makes them robust.
$env:PYTHONUTF8 = '1'

# 1. Sync Toolkit (Skills & Scripts)
Write-Host "Syncing Open Source Toolkit..." -ForegroundColor Gray
uv run .ai/scripts/publish_toolkit.py

# 2. Generate Engineering Specs
Write-Host "Generating High-Fidelity Specs..." -ForegroundColor Gray
uv run .ai/scripts/generate_spec.py

# 3. Hugo Build
Write-Host "Building Site (Hugo)..." -ForegroundColor Gray
cd site
uvx hugo --cleanDestinationDir
if ($LASTEXITCODE -ne 0) { Write-Error "Hugo build failed."; exit 1 }

# 4. Firebase Deploy
Write-Host "Deploying to Firebase..." -ForegroundColor Gray
npx firebase-tools deploy --only hosting:documentation
if ($LASTEXITCODE -ne 0) { Write-Error "Firebase deployment failed."; exit 1 }

Write-Host "Global Sync Complete! Site is live." -ForegroundColor Green
cd ..
