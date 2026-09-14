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

Write-Host 'NR7-1 STEP 0: Normal Run synthetic selftest'
& $Python (Join-Path $RepoRoot 'tests\selftest_normal_run.py')
$selfCode = $LASTEXITCODE
if ($selfCode -ne 0) {
  Write-Host "NR7-1 FAIL: selftest failed. exit=$selfCode"
  exit $selfCode
}

Write-Host ''
Write-Host 'NR7-1 STEP A: optimized Normal Run rebuild + safe snapshot'
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
$elapsed = [Math]::Round($sw.Elapsed.TotalSeconds, 3)
Write-Host ("Normal Run elapsed: {0:N3}s" -f $elapsed)

$oldReference = 380.62
$performancePath = Join-Path $outputDir ("NR7_1_{0}_performance.json" -f $Symbol)
$performance = [ordered]@{
  test = 'NR7-1_NORMAL_RUN_PERFORMANCE'
  symbol = $Symbol
  old_reference_seconds = $oldReference
  optimized_elapsed_seconds = $elapsed
  improved_vs_old_reference = ($elapsed -lt $oldReference)
  hard_acceptance_threshold_fixed = $false
  note = 'Performance is recorded for audit; no hard production threshold has been fixed yet.'
}
$performance | ConvertTo-Json -Depth 4 | Set-Content -Path $performancePath -Encoding UTF8

Write-Host ''
Write-Host 'NR7-1 STEP B: baseline-current vs published rebuilt-current regression'
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

Write-Host ''
Write-Host 'NR7-1 STEP C: failed-publication retention probe'
$snapshot = Join-Path $outputDir ("NORMAL_{0}_live_snapshot.csv" -f $Symbol)
$retentionReport = Join-Path $outputDir ("NR7_1_{0}_retention.json" -f $Symbol)
& $Python (Join-Path $RepoRoot 'tools\nr7_1_safe_retention.py') `
  '--symbol' $Symbol `
  '--snapshot' $snapshot `
  '--report' $retentionReport
$retentionCode = $LASTEXITCODE
if ($retentionCode -ne 0) {
  Write-Host "NR7-1 FAIL: safe snapshot retention probe failed. exit=$retentionCode"
  exit $retentionCode
}

Write-Host ''
Write-Host 'NR7-1 AUTOMATED FINAL CHECK PASS'
Write-Host ("Performance: {0}" -f $performancePath)
Write-Host ("Regression:  {0}" -f (Join-Path $outputDir ("NR7_1_{0}_regression.json" -f $Symbol)))
Write-Host ("Retention:   {0}" -f $retentionReport)
Write-Host ''
Write-Host 'Already evidenced on MT4: D1/H4/H1/M15 renderer = 16 objects each; H1 current+previous object generations present.'
Write-Host 'Remaining strict closure check: actual MT4 renderer must keep existing NCA_DRAW__ objects when its snapshot is unavailable/invalid.'
