param(
  [string]$BrokerSymbol = 'USDJPY#',
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$nvtOutput = Join-Path $common 'nvt_output'
$diffDir = Join-Path $nvtOutput 'nvt3_diff'
New-Item -ItemType Directory -Force -Path $diffDir | Out-Null

function Safe-FileSymbol([string]$Value) {
  return ($Value -replace '[<>:"/\\|?*]', '_')
}

$safe = Safe-FileSymbol $BrokerSymbol

Write-Host 'NVT3 STEP 0: synthetic diff selftest'
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt3.py')
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT3 SELFTEST FAILED exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

$gtDir = Join-Path $RepoRoot 'nvt\ground_truth'
$gtFiles = @(Get-ChildItem -Path $gtDir -Filter 'GT_*.json' | Where-Object { $_.Name -ne 'GT_TEMPLATE.json' } | Sort-Object Name)
if ($gtFiles.Count -eq 0) {
  Write-Host 'NVT3 FAIL: no Ground Truth cases found.'
  exit 2
}

$generated = @()
Write-Host ''
Write-Host 'NVT3 TEACHER-NCA DIFF START'
Write-Host "Broker symbol: $BrokerSymbol"
Write-Host "Cases: $($gtFiles.Count)"
Write-Host ''

foreach ($gtFile in $gtFiles) {
  $gt = Get-Content -Raw -Path $gtFile.FullName | ConvertFrom-Json
  $caseId = $gt.case_id
  $sourceId = $gt.source_id
  $tf = $gt.timeframe
  $candidate = Join-Path (Join-Path $nvtOutput $sourceId) ("candidates_{0}_{1}.json" -f $safe, $tf)
  $report = Join-Path $diffDir ("diff_{0}.json" -f $caseId)

  if (!(Test-Path $candidate)) {
    Write-Host ("{0}: WAITING candidate dump {1}" -f $caseId, $candidate)
    continue
  }

  & $Python (Join-Path $RepoRoot 'tools\nvt\compare_teacher.py') `
    '--ground-truth' $gtFile.FullName `
    '--candidate-dump' $candidate `
    '--output' $report `
    '--anchor-tolerance-bars' '1'

  if ($LASTEXITCODE -ne 0) {
    Write-Host ("NVT3 TOOL ERROR: {0} exit={1}" -f $caseId, $LASTEXITCODE)
    exit $LASTEXITCODE
  }

  $r = Get-Content -Raw -Path $report | ConvertFrom-Json
  Write-Host ("{0}: {1} failures=[{2}]" -f $caseId, $r.assessment_status, (($r.failure_classes -join ', ')))
  $generated += $report
}

if ($generated.Count -eq 0) {
  Write-Host ''
  Write-Host 'NVT3 WAITING: no candidate-backed case could be compared.'
  Write-Host 'Run NCA_NVT_HistoryExporter and RUN_NVT2_USDJPY_CORPUS.cmd first.'
  exit 2
}

$metrics = Join-Path $nvtOutput 'NVT3_USDJPY_METRICS.json'
& $Python (Join-Path $RepoRoot 'tools\nvt\scoring.py') `
  '--input-dir' $diffDir `
  '--output' $metrics
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT3 SCORING TOOL ERROR exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT3 DIFF GENERATION COMPLETE'
Write-Host "Generated reports: $($generated.Count)"
Write-Host "Metrics: $metrics"
Write-Host ''
Write-Host 'NOTE: FAIL means Teacher/NCA mismatch evidence, not a runner failure.'
Write-Host 'PENDING_GROUND_TRUTH means exact teacher anchors are not locked yet.'
Write-Host 'No production NCA code/state/snapshot/MT4 object was modified.'
