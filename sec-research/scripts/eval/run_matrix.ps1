# scripts/eval/run_matrix.ps1 — serialized GGUF authoring-reliability matrix for hb-0vq.
#
# Launches ONE llama-server at a time (8 GB VRAM ceiling), waits for /health,
# runs the authoring eval against that model, then frees VRAM before the next.
# Run from the sec-research/ root:
#   pwsh scripts/eval/run_matrix.ps1 -Track a -Trials 20
#   $env:VERIFY_LIVE=1; $env:LLM_LIVE=1; pwsh scripts/eval/run_matrix.ps1 -Track b -Trials 10
param(
  [int]$Trials = 10,
  [ValidateSet("a", "b", "both")][string]$Track = "both",
  [string]$ReportDir = "runtime/eval/$(Get-Date -Format yyyy-MM-dd)"
)

$ErrorActionPreference = "Stop"
$models = @(
  "qwen2.5-coder-7b-Q4_K_M.gguf",   # tooling / structured JSON
  "deepseek-r1-7b-Q4_K_M.gguf",     # reasoning
  "gemma-4-E4B-it-Q4_K_M.gguf",     # Aether classifier baseline
  "gemma3-4b-Q4_K_M.gguf",
  "phi4-mini-Q4_K_M.gguf"
)

New-Item -ItemType Directory -Force $ReportDir | Out-Null
$env:SECRESEARCH_LLM_PROVIDER = "llama"

foreach ($m in $models) {
  Write-Host "=== $m ===" -ForegroundColor Cyan
  $srv = Start-Process -PassThru -WindowStyle Hidden "C:\llama\llama-server.exe" `
    -ArgumentList @("-m", "C:\models\$m", "--ctx-size", "8192", "--n-gpu-layers", "99",
      "--flash-attn", "on", "--cache-type-k", "q8_0", "--cache-type-v", "q8_0", "--seed", "42")
  try {
    # Block until the server reports healthy (cold load can take ~40 s).
    $deadline = (Get-Date).AddSeconds(120)
    do {
      Start-Sleep 2
      $ok = try { (Invoke-RestMethod http://127.0.0.1:8080/health).status -eq "ok" } catch { $false }
    } until ($ok -or (Get-Date) -gt $deadline)
    if (-not $ok) { Write-Warning "llama-server for $m never became healthy; skipping"; continue }

    $env:SECRESEARCH_LLAMA_MODEL = $m
    $report = Join-Path $ReportDir ("{0}.json" -f ($m -replace '\.gguf$', ''))
    python scripts/eval/authoring_eval.py --track $Track --trials $Trials --report $report
  }
  finally {
    Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue   # free VRAM before the next model
    Start-Sleep 2
  }
}
Write-Host "Reports written to $ReportDir" -ForegroundColor Green
