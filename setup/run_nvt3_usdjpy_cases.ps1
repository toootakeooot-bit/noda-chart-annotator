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
$gtDir = Join-Path $RepoRoot 'nvt\ground_truth'

Write-Host 'NVT3 STEP 0A: Ground Truth JSON validation'
& $Python (Join-Path $RepoRoot 'tools\nvt\validate_ground_truth.py') '--ground-truth-dir' $gtDir
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT3 FAIL: Ground Truth validation failed exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}
Write-Host ''

Write-Host 'NVT3 STEP 0B: synthetic diff selftest'
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt3.py')
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT3 SELFTEST FAILED exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

# Score only reports generated in this run. Clear prior NVT research diffs only.
Get-ChildItem -Path $diffDir -Filter 'diff_*.json' -ErrorAction SilentlyContinue | Remove-Item -Force

$caseIndex = Join-Path $nvtOutput 'NVT3_CASE_INDEX.tsv'

# Python parses UTF-8 Ground Truth and exports an ASCII-only case index.
& $Python (Join-Path $RepoRoot 'tools\nvt\build_case_index.py') `
  '--ground-truth-dir' $gtDir `
  '--symbol' 'USDJPY' `
  '--output-tsv' $caseIndex
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT3 FAIL: case-index generation failed exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

$cases = @(Import-Csv -Path $caseIndex -Delimiter "`t")
if ($cases.Count -eq 0) {
  Write-Host 'NVT3 FAIL: no Ground Truth cases found.'
  exit 2
}

$generated = @()
$waiting = @()
Write-Host ''
Write-Host 'NVT3 TEACHER-NCA DIFF START'
Write-Host "Broker symbol: $BrokerSymbol"
Write-Host "Cases: $($cases.Count)"
Write-Host ''

foreach ($case in $cases) {
  $caseId = [string]$case.case_id
  $sourceId = [string]$case.source_id
  $tf = [string]$case.timeframe
  $gtPath = [string]$case.ground_truth_path
  $candidate = Join-Path (Join-Path $nvtOutput $sourceId) ("candidates_{0}_{1}.json" -f $safe, $tf)
  $report = Join-Path $diffDir ("diff_{0}.json" -f $caseId)

  if (!(Test-Path $candidate)) {
    Write-Host ("{0}: WAITING candidate dump {1}" -f $caseId, $candidate)
    $waiting += $caseId
    continue
  }

  & $Python (Join-Path $RepoRoot 'tools\nvt\compare_teacher.py') `
    '--ground-truth' $gtPath `
    '--candidate-dump' $candidate `
    '--output' $report `
    '--anchor-tolerance-bars' '1'

  if ($LASTEXITCODE -ne 0) {
    Write-Host ("NVT3 TOOL ERROR: {0} exit={1}" -f $caseId, $LASTEXITCODE)
    exit $LASTEXITCODE
  }

  Write-Host ("{0}: report generated -> {1}" -f $caseId, $report)
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
Write-Host "Waiting cases: $($waiting.Count)"
if ($waiting.Count -gt 0) {
  Write-Host ("Waiting: {0}" -f ($waiting -join ', '))
}
Write-Host "Metrics: $metrics"
Write-Host ''
Write-Host 'NOTE: FAIL means Teacher/NCA mismatch evidence, not a runner failure.'
Write-Host 'PENDING_GROUND_TRUTH means exact teacher anchors are not locked yet.'
Write-Host 'Ground Truth is syntax-validated before comparison.'
Write-Host 'Ground Truth JSON parsing is owned by Python; PowerShell 5.1 does not parse teacher-evidence JSON.'
Write-Host 'Only NVT research diff_*.json from a prior run are cleared; production files are untouched.'
Write-Host 'No production NCA code/state/snapshot/MT4 object was modified.'