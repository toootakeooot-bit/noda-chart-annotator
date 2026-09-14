param(
  [Parameter(Mandatory=$true)]
  [string]$Symbol,
  [string]$TestId = 'NR7-SYMBOL',
  [string]$Python = 'python',
  [double]$ReferenceSeconds = 0
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$inputDir = Join-Path $common 'live_input'
$outputDir = Join-Path $common 'live_output'
New-Item -ItemType Directory -Force -Path $inputDir | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

function Safe-FileSymbol([string]$Value) {
  return ($Value -replace '[<>:"/\\|?*]', '_')
}

$safe = Safe-FileSymbol $Symbol
$required = @('D1','H4','H1','M15') | ForEach-Object {
  Join-Path $inputDir ("NORMAL_{0}_{1}.csv" -f $safe, $_)
}
$missing = @($required | Where-Object { !(Test-Path $_) })
if ($missing.Count -gt 0) {
  Write-Host "$TestId WAITING FOR MT4 EXPORT"
  Write-Host "Open $Symbol in MT4 and run NCA_NormalRun_Exporter once."
  Write-Host 'Missing:'
  $missing | ForEach-Object { Write-Host "  $_" }
  exit 2
}

Write-Host "$TestId STEP 0: shared Normal Run synthetic selftest"
& $Python (Join-Path $RepoRoot 'tests\selftest_normal_run.py')
if ($LASTEXITCODE -ne 0) {
  Write-Host "$TestId FAIL: selftest failed. exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host "$TestId STEP A: Normal Run rebuild + safe snapshot for $Symbol"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
& $Python (Join-Path $RepoRoot 'tools\run_normal.py') `
  '--symbol' $Symbol `
  '--input-dir' $inputDir `
  '--output-dir' $outputDir
$normalCode = $LASTEXITCODE
$sw.Stop()
if ($normalCode -ne 0) {
  Write-Host "$TestId FAIL: Normal Run failed; last valid drawing should remain unchanged. exit=$normalCode"
  exit $normalCode
}
$elapsed = [Math]::Round($sw.Elapsed.TotalSeconds, 3)
Write-Host ("Normal Run elapsed: {0:N3}s" -f $elapsed)

$performancePath = Join-Path $outputDir ("{0}_{1}_performance.json" -f $TestId, $safe)
$performance = [ordered]@{
  test = "${TestId}_PERFORMANCE"
  symbol = $Symbol
  elapsed_seconds = $elapsed
  reference_seconds = $(if ($ReferenceSeconds -gt 0) { $ReferenceSeconds } else { $null })
  improved_vs_reference = $(if ($ReferenceSeconds -gt 0) { $elapsed -lt $ReferenceSeconds } else { $null })
  hard_acceptance_threshold_fixed = $false
  note = 'Elapsed time is recorded for audit; no cross-symbol hard production threshold is fixed.'
}
$performance | ConvertTo-Json -Depth 4 | Set-Content -Path $performancePath -Encoding UTF8

Write-Host ''
Write-Host "$TestId STEP B: structural-event baseline vs published Normal Run state"
$regressionPath = Join-Path $outputDir ("{0}_{1}_regression.json" -f $TestId, $safe)
& $Python (Join-Path $RepoRoot 'tools\nr7_symbol_regression.py') `
  '--symbol' $Symbol `
  '--baseline-symbol' $Symbol `
  '--test-id' "${TestId}_REGRESSION" `
  '--input-dir' $inputDir `
  '--output-dir' $outputDir `
  '--report' $regressionPath
$regCode = $LASTEXITCODE
if ($regCode -ne 0) {
  Write-Host "$TestId FAIL: symbol regression mismatch. exit=$regCode"
  Write-Host "Report: $regressionPath"
  exit $regCode
}

Write-Host ''
Write-Host "$TestId STEP C: failed-publication retention probe"
$snapshot = Join-Path $outputDir ("NORMAL_{0}_live_snapshot.csv" -f $safe)
$retentionPath = Join-Path $outputDir ("{0}_{1}_retention.json" -f $TestId, $safe)
& $Python (Join-Path $RepoRoot 'tools\nr7_safe_retention.py') `
  '--symbol' $Symbol `
  '--test-id' "${TestId}_SAFE_SNAPSHOT_RETENTION" `
  '--snapshot' $snapshot `
  '--report' $retentionPath
$retentionCode = $LASTEXITCODE
if ($retentionCode -ne 0) {
  Write-Host "$TestId FAIL: safe snapshot retention probe failed. exit=$retentionCode"
  exit $retentionCode
}

try {
  $reg = Get-Content -Raw -Path $regressionPath | ConvertFrom-Json
  Write-Host ''
  Write-Host 'Expected renderer rows from validated snapshot:'
  foreach ($tf in @('D1','H4','H1','M15')) {
    $count = $reg.snapshot.rows_by_timeframe.$tf
    Write-Host ("  {0}: {1} objects" -f $tf, $count)
  }
} catch {
  Write-Host 'Snapshot count summary could not be displayed; regression report itself is still authoritative.'
}

Write-Host ''
Write-Host "$TestId AUTOMATED CHECK PASS"
Write-Host "Symbol:      $Symbol"
Write-Host "Performance: $performancePath"
Write-Host "Regression:  $regressionPath"
Write-Host "Retention:   $retentionPath"
Write-Host "Snapshot:    $snapshot"
Write-Host ''
Write-Host 'Remaining host evidence: run NCA_NormalRun_Renderer once on each D1/H4/H1/M15 chart and compare object counts to the values above.'
