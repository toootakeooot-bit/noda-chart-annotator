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
$code = $LASTEXITCODE
if ($code -eq 2) {
  Write-Host 'NCA LIVE DRAW USDJPY TEST WAITING: no MT4 OHLC input files yet.'
  Write-Host 'Compile/attach NCA_TEST_MarketExporter to one USDJPY# chart in TEST MT4, then run this script again.'
  exit 2
}
if ($code -eq 3) {
  Write-Host 'NCA LIVE DRAW USDJPY TEST PARTIAL INPUT: one or more TF CSV files are missing.'
  exit 3
}
if ($code -ne 0) { throw "Live Draw TEST runner failed: $code" }
Write-Host 'NCA LIVE DRAW USDJPY TEST RUN PASS'
