# publish.ps1
# Agentic Workspace - Local CI/CD Orchestrator (v1.1)
# Use: .\publish.ps1

# Skip valve: WORKSPACE_SKIP_PUBLISH=1 lets a docs/.ai commit land without a live deploy
# (e.g. when site/ has unrelated uncommitted edits). The hook output names the skip, so it is auditable.
if ($env:WORKSPACE_SKIP_PUBLISH -eq '1') {
    Write-Host "Skip-publish valve: WORKSPACE_SKIP_PUBLISH=1 is set. No publish." -ForegroundColor Yellow
    exit 0
}

# Skip-publish guard: if the most recent commit only changed sec-research/ paths,
# skip the entire pipeline. sec-research/ is operational data (findings, programs,
# evidence) — NOT documentation to publish. Avoids unnecessary Cloudflare redeploys
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

# 4. Privacy gate: the web platform's scrub-check over the built output (path dependency on
#    the sibling websites repo; build it there with `pnpm turbo run build` if dist is missing).
Write-Host "Privacy gate (scrub-check)..." -ForegroundColor Gray
$scrub = Join-Path $PSScriptRoot 'websites\packages\tools\dist\cli\scrub-check.js'
node $scrub public
if ($LASTEXITCODE -ne 0) { Write-Error "scrub-check blocked the publish (see hits above)."; cd ..; exit 1 }

# 5. Cloudflare deploy. The token lives in a 1Password vault the automation service account
#    cannot read, so this pops one Windows Hello prompt; dismissing it skips the deploy.
Write-Host "Deploying to Cloudflare (approve the Windows Hello prompt)..." -ForegroundColor Gray
Import-Module (Join-Path $HOME 'scripts\lib\Secrets.psm1') -Force
$wrangler = Join-Path $PSScriptRoot 'websites\apps\garrettmanley-com\node_modules\.bin\wrangler.cmd'
Invoke-WithSecrets -Interactive -EnvFile (Join-Path $PWD '.env.tpl') -- $wrangler deploy
if ($LASTEXITCODE -ne 0) { Write-Error "Cloudflare deployment failed or was not approved."; cd ..; exit 1 }

Write-Host "Global Sync Complete! Site is live." -ForegroundColor Green
cd ..
