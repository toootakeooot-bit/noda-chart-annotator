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

function Read-JsonUtf8([string]$Path) {
  # Windows PowerShell 5.1 may misread BOM-less UTF-8 JSON containing Japanese
  # when Get-Content uses the system ANSI code page. Read explicitly as UTF-8.
  $text = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
  return ($text | ConvertFrom-Json)
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
$waiting = @()
Write-Host ''
Write-Host 'NVT3 TEACHER-NCA DIFF START'
Write-Host "Broker symbol: $BrokerSymbol"
Write-Host "Cases: $($gtFiles.Count)"
Write-Host ''

foreach ($gtFile in $gtFiles) {
  try {
    $gt = Read-JsonUtf8 $gtFile.FullName
  }
  catch {
    Write-Host ("NVT3 FAIL: invalid/unreadable UTF-8 Ground Truth JSON {0}" -f $gtFile.FullName)
    Write-Host $_.Exception.Message
    exit 3
  }

  $caseId = [string]$gt.case_id
  $sourceId = [string]$gt.source_id
  $tf = [string]$gt.timeframe
  $candidate = Join-Path (Join-Path $nvtOutput $sourceId) ("candidates_{0}_{1}.json" -f $safe, $tf)
  $report = Join-Path $diffDir ("diff_{0}.json" -f $caseId)

  if (!(Test-Path $candidate)) {
    Write-Host ("{0}: WAITING candidate dump {1}" -f $caseId, $candidate)
    $waiting += $caseId
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

  try {
    $r = Read-JsonUtf8 $report
  }
  catch {
    Write-Host ("NVT3 FAIL: generated report is unreadable JSON: {0}" -f $report)
    Write-Host $_.Exception.Message
    exit 3
  }

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
Write-Host "Waiting cases: $($waiting.Count)"
if ($waiting.Count -gt 0) {
  Write-Host ("Waiting: {0}" -f ($waiting -join ', '))
}
Write-Host "Metrics: $metrics"
Write-Host ''
Write-Host 'NOTE: FAIL means Teacher/NCA mismatch evidence, not a runner failure.'
Write-Host 'PENDING_GROUND_TRUTH means exact teacher anchors are not locked yet.'
Write-Host 'Ground Truth/report JSON is read explicitly as UTF-8 for Windows PowerShell 5.1 compatibility.'
Write-Host 'No production NCA code/state/snapshot/MT4 object was modified.'
