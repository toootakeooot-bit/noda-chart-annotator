param(
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$inputDir = Join-Path $common 'live_input'
$outputDir = Join-Path $common 'live_output'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

& $Python (Join-Path $RepoRoot 'tools\run_live_draw_test_usdjpy.py') --input-dir $inputDir --output-dir $outputDir
if ($LASTEXITCODE -ne 0) { throw "Live Draw TEST runner failed: $LASTEXITCODE" }
Write-Host 'NCA LIVE DRAW USDJPY TEST RUN PASS'
