param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$inputDir = Join-Path $common 'live_input'
$outputDir = Join-Path $common 'live_output'

New-Item -ItemType Directory -Force -Path $inputDir | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$required = @('D1','H4','H1','M15') | ForEach-Object {
  Join-Path $inputDir ("NORMAL_{0}_{1}.csv" -f $Symbol, $_)
}
$missing = @($required | Where-Object { !(Test-Path $_) })
if ($missing.Count -gt 0) {
  Write-Host 'NR7-1 WAITING FOR MT4 EXPORT'
  Write-Host 'Open USDJPY# in MT4 and run NCA_NormalRun_Exporter once.'
  Write-Host 'Missing:'
  $missing | ForEach-Object { Write-Host "  $_" }
  exit 2
}

Write-Host 'NR7-1 STEP A: Normal Run rebuild + safe snapshot'
$sw = [System.Diagnostics.Stopwatch]::StartNew()
& $Python (Join-Path $RepoRoot 'tools\run_normal.py') `
  '--symbol' $Symbol `
  '--input-dir' $inputDir `
  '--output-dir' $outputDir
$normalCode = $LASTEXITCODE
$sw.Stop()
if ($normalCode -ne 0) {
  Write-Host "NR7-1 FAIL: Normal Run failed; last valid drawing should remain unchanged. exit=$normalCode"
  exit $normalCode
}
Write-Host ("Normal Run elapsed: {0:N2}s" -f $sw.Elapsed.TotalSeconds)

Write-Host 'NR7-1 STEP B: baseline-current vs rebuilt-current regression'
& $Python (Join-Path $RepoRoot 'tools\nr7_1_usdjpy_regression.py') `
  '--symbol' $Symbol `
  '--baseline-symbol' 'USDJPY' `
  '--input-dir' $inputDir `
  '--output-dir' $outputDir
$regCode = $LASTEXITCODE
if ($regCode -ne 0) {
  Write-Host "NR7-1 FAIL: regression mismatch. exit=$regCode"
  Write-Host ("Report: {0}" -f (Join-Path $outputDir ("NR7_1_{0}_regression.json" -f $Symbol)))
  exit $regCode
}

Write-Host 'NR7-1 AUTOMATED CHECK PASS'
Write-Host ("Report: {0}" -f (Join-Path $outputDir ("NR7_1_{0}_regression.json" -f $Symbol)))
Write-Host ''
Write-Host 'Remaining MT4 visual checks:'
Write-Host '  1. Run NCA_NormalRun_Renderer on USDJPY# D1/H4/H1/M15 charts.'
Write-Host '  2. Confirm current + previous TL/CH are visually reasonable.'
Write-Host '  3. Confirm any manual objects remain untouched.'
Write-Host '  4. Capture screenshots for audit if required.'
