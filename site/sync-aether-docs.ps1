#requires -Version 7
<#
.SYNOPSIS
    Sync Aether Engine player-facing docs into the Hextra site as a public /aether/ section.

.DESCRIPTION
    Reads the player/GM guides from the Aether repo (docs/user), strips each doc's internal
    frontmatter, injects Hugo/Hextra frontmatter (title + ordering weight), rewrites links so
    the published site carries no broken or internal references, and writes them under
    content/aether/ (plus a section _index.md). docs/user is the SOURCE OF TRUTH; this script
    is idempotent — re-run it after the source docs change. It does NOT build, commit, or deploy.

.EXAMPLE
    .\sync-aether-docs.ps1
    Then build/preview:  uvx hugo server   (from this directory)
#>
$ErrorActionPreference = 'Stop'

$srcDir  = Join-Path $PSScriptRoot '..\Roleplaying\docs\user' | Resolve-Path
$destDir = Join-Path $PSScriptRoot 'content\aether'

# Ordered player-first, then GM. basename (no .md) => display title + sidebar weight.
$docs = [ordered]@{
    'player-onboarding'       = @{ Title = 'Player Onboarding';             Weight = 10 }
    'character-creation'      = @{ Title = 'Character Creation';            Weight = 20 }
    'tutorial-first-campaign' = @{ Title = 'Tutorial: Your First Campaign'; Weight = 30 }
    'player-manual'           = @{ Title = 'Player Manual';                 Weight = 40 }
    'aether-cli'              = @{ Title = 'Playing via the CLI';           Weight = 50 }
    'auth-troubleshooting'    = @{ Title = 'Auth Troubleshooting';          Weight = 60 }
    'gm-onboarding-manual'    = @{ Title = 'GM Onboarding';                 Weight = 70 }
    'gm-manual'               = @{ Title = 'GM Manual';                     Weight = 80 }
    'claude-as-gm'            = @{ Title = 'Claude as GM';                  Weight = 90 }
}

if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }

foreach ($base in $docs.Keys) {
    $srcPath = Join-Path $srcDir "$base.md"
    if (-not (Test-Path $srcPath)) { Write-Warning "missing source: $srcPath"; continue }

    $body = Get-Content -Raw -LiteralPath $srcPath
    # Strip the leading frontmatter block (--- ... ---).
    $body = [regex]::Replace($body, '(?s)\A---\r?\n.*?\r?\n---\r?\n', '')

    # Drop the body's leading H1 — Hextra renders the frontmatter title as the page
    # heading, so a body "# Title" would render as a duplicate heading.
    $body = [regex]::Replace($body, '(?s)\A\s*#[ \t]+[^\r\n]*\r?\n+', '')

    # Pass 1: published siblings -> /aether/<base>/ (preserve optional #anchor).
    foreach ($b in $docs.Keys) {
        $body = $body -replace "\]\($([regex]::Escape($b))\.md(#[^)]*)?\)", "](/aether/$b/`$1)"
    }
    # Pass 2: private-repo links -> plain text (would 404 publicly + leak the private repo).
    $body = $body -replace '\[([^\]]+)\]\(https?://github\.com/GarrettManley/aether-engine[^)]*\)', '$1'
    # Pass 2b: redact the PRIVATE repo coordinate in ANY form -- bare https/SSH URLs in code
    # fences (e.g. `git clone git@github.com:GarrettManley/aether-engine.git`) that the
    # markdown-link passes cannot see. The owner/slug coordinate must never reach published output.
    $body = $body -replace 'git@github\.com:GarrettManley/aether-engine(\.git)?', '<your-aether-engine-remote>'
    $body = $body -replace 'https?://github\.com/GarrettManley/aether-engine(\.git)?', '<your-aether-engine-remote>'
    # Pass 2c: an internal engineering doc whose link TEXT is itself a repo path leaks structure
    # (e.g. `docs/engineering/plans/...md`). Drop the whole reference; titled engineering links
    # keep their human title via Pass 3 below.
    $body = [regex]::Replace($body, '\[`[^\]]*?(?:docs/)?engineering/[^\]]*?`\]\([^)]*\)', 'internal design notes')
    # Pass 3: remaining internal/relative .md/.json links -> plain text (not published).
    $body = $body -replace '\[([^\]]+)\]\((?!https?://|/aether/)[^)]*\.(?:md|json)(?:#[^)]*)?\)', '$1'
    # Pass 4: drop private-tracker issue numbers that appear as parenthetical asides -- no public
    # utility and they disclose internal tracker structure. Inline prose refs are left intact to
    # avoid mangling sentences ("(#138)", "(#138, #139)", "(spec 043, #138)" are handled).
    $body = $body -replace '\s*\(#\d+(?:[,/]\s*#\d+)*\)', ''
    $body = $body -replace '\((spec [^),]+?)(?:,\s*(?:issue\s+)?#\d+(?:[,/]\s*#\d+)*)\)', '($1)'

    # Fail-closed: never publish the private repo coordinate. If any pass above missed it, abort
    # the whole sync rather than silently leak (the previous design failed OPEN on bare URLs).
    if ($body -match 'github\.com[:/]GarrettManley/aether-engine') {
        throw "ABORT: private repo coordinate 'GarrettManley/aether-engine' survived redaction in '$base' -- fix the source or the stripper before re-running."
    }

    $meta = $docs[$base]
    $fm = "---`ntitle: `"$($meta.Title)`"`nweight: $($meta.Weight)`n---`n`n"
    Set-Content -LiteralPath (Join-Path $destDir "$base.md") -Value ($fm + $body) -Encoding utf8
    Write-Host "synced  $base"
}

# Section landing page.
$index = @'
---
title: "Aether Engine"
weight: 5
---

Player and Game-Master guides for the **Aether Engine** — a tabletop RPG framework that pairs
LLM-driven narrative with a deterministic Rust rules core and an immutable, hash-linked campaign
ledger. New here? Start with onboarding, then the tutorial.

## Players
- [Player Onboarding](/aether/player-onboarding/)
- [Character Creation](/aether/character-creation/)
- [Tutorial: Your First Campaign](/aether/tutorial-first-campaign/)
- [Player Manual](/aether/player-manual/)
- [Playing via the CLI](/aether/aether-cli/)
- [Auth Troubleshooting](/aether/auth-troubleshooting/)

## Game Masters
- [GM Onboarding](/aether/gm-onboarding-manual/)
- [GM Manual](/aether/gm-manual/)
- [Claude as GM](/aether/claude-as-gm/)
'@
Set-Content -LiteralPath (Join-Path $destDir '_index.md') -Value $index -Encoding utf8
Write-Host "wrote   _index.md"
Write-Host ""
Write-Host "Done. Preview with:  uvx hugo server   (from $PSScriptRoot)" -ForegroundColor Green
