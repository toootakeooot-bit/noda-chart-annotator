param(
  [string]$BrokerSymbol = 'USDJPY#',
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$inputDir = Join-Path $common 'nvt_input'
$outputRoot = Join-Path $common 'nvt_output'
New-Item -ItemType Directory -Force -Path $inputDir | Out-Null
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

function Safe-FileSymbol([string]$Value) {
  return ($Value -replace '[<>:"/\\|?*]', '_')
}

function Read-JsonUtf8([string]$Path) {
  $text = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
  return ($text | ConvertFrom-Json)
}

$safe = Safe-FileSymbol $BrokerSymbol
$gtDir = Join-Path $RepoRoot 'nvt\ground_truth'
$cutoffManifestPath = Join-Path $RepoRoot 'nvt\manifests\USDJPY_EXPECTED_MARKET_CUTOFFS_V1.json'

if (!(Test-Path $cutoffManifestPath)) {
  Write-Host "NVT2 FAIL: cutoff manifest missing: $cutoffManifestPath"
  exit 2
}

$cutoffManifest = Read-JsonUtf8 $cutoffManifestPath
$cutoffBySource = @{}
foreach ($src in $cutoffManifest.sources) {
  $cutoffBySource[[string]$src.source_id] = ([string]$src.expected_last_market_date + 'T23:59:59')
}

$gtFiles = @(Get-ChildItem -Path $gtDir -Filter 'GT_*.json' | Where-Object { $_.Name -ne 'GT_TEMPLATE.json' } | Sort-Object Name)
if ($gtFiles.Count -eq 0) {
  Write-Host 'NVT2 FAIL: no Ground Truth cases found.'
  exit 2
}

# Build only the source/timeframe pairs currently required by Ground Truth.
# This prevents optional/unneeded M15 history from blocking D1/H4/H1 research.
$pairMap = @{}
foreach ($gtFile in $gtFiles) {
  $gt = Read-JsonUtf8 $gtFile.FullName
  if ([string]$gt.symbol -ne 'USDJPY') { continue }
  $sourceId = [string]$gt.source_id
  $tf = [string]$gt.timeframe
  if (!$cutoffBySource.ContainsKey($sourceId)) {
    Write-Host "NVT2 FAIL: no cutoff manifest entry for $sourceId"
    exit 2
  }
  $key = "$sourceId|$tf"
  if (!$pairMap.ContainsKey($key)) {
    $pairMap[$key] = [pscustomobject]@{
      SourceId = $sourceId
      Timeframe = $tf
      Cutoff = $cutoffBySource[$sourceId]
      Cases = @()
    }
  }
  $pairMap[$key].Cases += [string]$gt.case_id
}

$pairs = @($pairMap.Values | Sort-Object SourceId, Timeframe)
if ($pairs.Count -eq 0) {
  Write-Host 'NVT2 FAIL: no USDJPY Ground Truth source/timeframe pairs found.'
  exit 2
}

$requiredTfs = @($pairs | Select-Object -ExpandProperty Timeframe -Unique)
$missing = @()
foreach ($tf in $requiredTfs) {
  $src = Join-Path $inputDir ("NVT_{0}_{1}.csv" -f $safe, $tf)
  if (!(Test-Path $src)) { $missing += $src }
}
if ($missing.Count -gt 0) {
  Write-Host 'NVT2 WAITING FOR NVT DEEP-HISTORY EXPORT'
  Write-Host "Open $BrokerSymbol in MT4 and run NCA_NVT_HistoryExporter once."
  Write-Host 'This is separate from the production NCA_NormalRun_Exporter.'
  Write-Host 'Missing Ground-Truth-required files:'
  $missing | ForEach-Object { Write-Host "  $_" }
  exit 2
}

$summary = @()
Write-Host 'NVT2 USDJPY GROUND-TRUTH CANDIDATE DUMP START'
Write-Host "Broker data symbol: $BrokerSymbol"
Write-Host 'Teacher reference symbol: USDJPY'
Write-Host "NVT input: $inputDir"
Write-Host "Required source/TF pairs: $($pairs.Count)"
Write-Host "Required TFs: $($requiredTfs -join ', ')"
Write-Host 'NOTE: TFs not required by current Ground Truth are intentionally not gating this run.'
Write-Host ''

foreach ($pair in $pairs) {
  $sourceId = [string]$pair.SourceId
  $tf = [string]$pair.Timeframe
  $cutoff = [string]$pair.Cutoff
  $caseDir = Join-Path $outputRoot $sourceId
  New-Item -ItemType Directory -Force -Path $caseDir | Out-Null
  $src = Join-Path $inputDir ("NVT_{0}_{1}.csv" -f $safe, $tf)
  $out = Join-Path $caseDir ("candidates_{0}_{1}.json" -f $safe, $tf)

  Write-Host ("PAIR {0} {1} cutoff<={2} cases=[{3}]" -f $sourceId, $tf, $cutoff, ($pair.Cases -join ','))

  & $Python (Join-Path $RepoRoot 'tools\nvt\dump_candidates.py') `
    '--input-csv' $src `
    '--symbol' $BrokerSymbol `
    '--timeframe' $tf `
    '--cutoff' $cutoff `
    '--output' $out

  if ($LASTEXITCODE -ne 0) {
    Write-Host ("NVT2 FAIL REQUIRED PAIR: {0} {1} exit={2}" -f $sourceId, $tf, $LASTEXITCODE)
    Write-Host 'The required TF does not have enough history for this Ground Truth case, or the dump tool failed.'
    Write-Host 'Optional TFs are not processed and cannot block this run.'
    exit $LASTEXITCODE
  }

  $payload = Read-JsonUtf8 $out
  $summary += [pscustomobject]@{
    source_id = $sourceId
    requested_cutoff = $cutoff
    timeframe = $tf
    ground_truth_cases = @($pair.Cases)
    broker_symbol = $BrokerSymbol
    effective_last_closed_bar = $payload.effective_last_closed_bar
    first_bar_time = $payload.first_bar_time
    closed_bar_count = $payload.closed_bar_count
    confirmed_turn_count = $payload.detector.confirmed_turn_count
    candidate_count = $payload.candidate_count
    selected_large_candidate_id = $payload.selected_large_candidate_id
    selected_mid_candidate_id = $payload.selected_mid_candidate_id
    output = $out
  }
  Write-Host ''
}

$summaryPath = Join-Path $outputRoot 'NVT2_USDJPY_GT_REQUIRED_SUMMARY.json'
$summaryJson = $summary | ConvertTo-Json -Depth 7
[System.IO.File]::WriteAllText($summaryPath, $summaryJson, (New-Object System.Text.UTF8Encoding($false)))

Write-Host 'NVT2 USDJPY GROUND-TRUTH CANDIDATE DUMP PASS'
Write-Host "Generated required pairs: $($summary.Count)"
Write-Host "Summary: $summaryPath"
Write-Host ''
Write-Host 'Important: teacher-video date cutoffs are provisional date-level upper bounds.'
Write-Host 'NVT5 will tighten each event to the exact verified market cutoff.'
Write-Host 'Optional TF history gaps do not invalidate unrelated Ground Truth cases.'
Write-Host 'Production live_input, Normal Run snapshot/state, and MT4 NCA_DRAW__ objects were not modified.'
