param(
  [string]$BrokerSymbol = 'USDJPY#',
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$inputDir = Join-Path $common 'nvt_input'
$outputRoot = Join-Path $common 'nvt_output'
$replayRoot = Join-Path $outputRoot 'nvt5_replay'
New-Item -ItemType Directory -Force -Path $replayRoot | Out-Null

function Safe-FileSymbol([string]$Value) {
  return ($Value -replace '[<>:"/\\|?*]', '_')
}

$safe = Safe-FileSymbol $BrokerSymbol
$gtDir = Join-Path $RepoRoot 'nvt\ground_truth'
$cutoffManifest = Join-Path $RepoRoot 'nvt\manifests\USDJPY_EXPECTED_MARKET_CUTOFFS_V1.json'
$planTsv = Join-Path $outputRoot 'NVT5_REPLAY_PLAN.tsv'
$resolvedJson = Join-Path $outputRoot 'NVT5_RESOLVED_CUTOFFS.json'

Write-Host 'NVT5 STEP 0: Ground Truth JSON validation'
& $Python (Join-Path $RepoRoot 'tools\nvt\validate_ground_truth.py') `
  '--ground-truth-dir' $gtDir `
  '--symbol' 'USDJPY'
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT5 FAIL: Ground Truth validation failed exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT5 STEP 1: resolve exact broker cutoffs from real XM closed bars'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt5_replay_plan.py') `
  '--ground-truth-dir' $gtDir `
  '--cutoff-manifest' $cutoffManifest `
  '--input-dir' $inputDir `
  '--broker-symbol' $BrokerSymbol `
  '--teacher-symbol' 'USDJPY' `
  '--output-tsv' $planTsv `
  '--output-json' $resolvedJson
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT5 FAIL: exact-cutoff resolution failed exit=$LASTEXITCODE"
  Write-Host 'Do not invent a replacement cutoff. Check NVT deep-history coverage.'
  exit $LASTEXITCODE
}

$plan = @(Import-Csv -Path $planTsv -Delimiter "`t")
if ($plan.Count -eq 0) {
  Write-Host 'NVT5 FAIL: replay plan is empty.'
  exit 2
}

Write-Host ''
Write-Host 'NVT5 STEP 2: deterministic time-frozen replays'
Write-Host "Required replay pairs: $($plan.Count)"
Write-Host "Replay root: $replayRoot"
Write-Host ''

$summary = @()
foreach ($pair in $plan) {
  $sourceId = [string]$pair.source_id
  $tf = [string]$pair.timeframe
  $cutoff = [string]$pair.exact_cutoff
  $cases = [string]$pair.cases
  $src = [string]$pair.input_csv
  $pairId = "PAIR__${sourceId}__${tf}"
  $pairDir = Join-Path $replayRoot $sourceId
  New-Item -ItemType Directory -Force -Path $pairDir | Out-Null
  $candidateOut = Join-Path $pairDir ("candidates_exact_{0}_{1}.json" -f $safe, $tf)

  Write-Host ("REPLAY {0} {1} exact_cutoff={2} cases=[{3}]" -f $sourceId, $tf, $cutoff, $cases)

  & $Python (Join-Path $RepoRoot 'tools\nvt\replay_to_time.py') `
    '--input-csv' $src `
    '--symbol' $BrokerSymbol `
    '--timeframe' $tf `
    '--cutoff' $cutoff `
    '--case-id' $pairId `
    '--output-dir' $pairDir
  if ($LASTEXITCODE -ne 0) {
    Write-Host ("NVT5 FAIL REPLAY: {0} {1} exit={2}" -f $sourceId, $tf, $LASTEXITCODE)
    exit $LASTEXITCODE
  }

  # Rebuild the exact candidate pool at the same verified cutoff.  This remains
  # read-only research and is used by the anchor-review workbench/NVT3 rerun.
  & $Python (Join-Path $RepoRoot 'tools\nvt\dump_candidates.py') `
    '--input-csv' $src `
    '--symbol' $BrokerSymbol `
    '--timeframe' $tf `
    '--cutoff' $cutoff `
    '--output' $candidateOut
  if ($LASTEXITCODE -ne 0) {
    Write-Host ("NVT5 FAIL CANDIDATE DUMP: {0} {1} exit={2}" -f $sourceId, $tf, $LASTEXITCODE)
    exit $LASTEXITCODE
  }

  $summary += [pscustomobject]@{
    source_id = $sourceId
    timeframe = $tf
    exact_cutoff = $cutoff
    ground_truth_cases = $cases
    frozen_bar_count = [int]$pair.frozen_bar_count
    excluded_future_bar_count = [int]$pair.excluded_future_bar_count
    candidate_dump = $candidateOut
  }
  Write-Host ''
}

$summaryPath = Join-Path $outputRoot 'NVT5_USDJPY_REPLAY_SUMMARY.json'
$summaryJson = $summary | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText($summaryPath, $summaryJson, (New-Object System.Text.UTF8Encoding($false)))

Write-Host 'NVT5 USDJPY TIME-FROZEN REPLAY PASS'
Write-Host "Resolved replay pairs: $($summary.Count)"
Write-Host "Resolved cutoffs: $resolvedJson"
Write-Host "Replay summary: $summaryPath"
Write-Host ''
Write-Host 'PASS means every required pair used an exact cutoff derived from actual XM closed-bar history.'
Write-Host 'No production Normal Run state/snapshot, MT4 NCA_DRAW__ object, or trade state was modified.'
Write-Host 'Teacher anchors remain UNKNOWN until source-frame/OHLC reconciliation; NVT5 does not guess them.'
