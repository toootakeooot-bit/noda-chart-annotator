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

$safe = Safe-FileSymbol $BrokerSymbol
$tfs = @('D1','H4','H1','M15')

$required = $tfs | ForEach-Object {
  Join-Path $inputDir ("NVT_{0}_{1}.csv" -f $safe, $_)
}
$missing = @($required | Where-Object { !(Test-Path $_) })
if ($missing.Count -gt 0) {
  Write-Host 'NVT2 WAITING FOR NVT DEEP-HISTORY EXPORT'
  Write-Host "Open $BrokerSymbol in MT4 and run NCA_NVT_HistoryExporter once."
  Write-Host 'This is separate from the production NCA_NormalRun_Exporter.'
  Write-Host 'Missing:'
  $missing | ForEach-Object { Write-Host "  $_" }
  exit 2
}

# Date-level upper bounds for the weekly teacher videos. The candidate-dump JSON
# records the actual final broker bar <= each bound. Exact decision cutoffs will
# later be tightened by NVT5 time-frozen replay.
$cases = @(
  [pscustomobject]@{ Id='NVT_VIDEO_20260808'; Cutoff='2026-08-07T23:59:59' },
  [pscustomobject]@{ Id='NVT_VIDEO_20260822'; Cutoff='2026-08-21T23:59:59' },
  [pscustomobject]@{ Id='NVT_VIDEO_20260830'; Cutoff='2026-08-28T23:59:59' },
  [pscustomobject]@{ Id='NVT_VIDEO_20260905'; Cutoff='2026-09-04T23:59:59' },
  [pscustomobject]@{ Id='NVT_VIDEO_20260912'; Cutoff='2026-09-11T23:59:59' }
)

$summary = @()
Write-Host 'NVT2 USDJPY CORPUS CANDIDATE DUMP START'
Write-Host "Broker data symbol: $BrokerSymbol"
Write-Host 'Teacher reference symbol: USDJPY'
Write-Host "NVT input: $inputDir"
Write-Host ''

foreach ($case in $cases) {
  $caseDir = Join-Path $outputRoot $case.Id
  New-Item -ItemType Directory -Force -Path $caseDir | Out-Null
  Write-Host ("CASE {0} cutoff<={1}" -f $case.Id, $case.Cutoff)

  foreach ($tf in $tfs) {
    $src = Join-Path $inputDir ("NVT_{0}_{1}.csv" -f $safe, $tf)
    $out = Join-Path $caseDir ("candidates_{0}_{1}.json" -f $safe, $tf)

    & $Python (Join-Path $RepoRoot 'tools\nvt\dump_candidates.py') `
      '--input-csv' $src `
      '--symbol' $BrokerSymbol `
      '--timeframe' $tf `
      '--cutoff' $case.Cutoff `
      '--output' $out

    if ($LASTEXITCODE -ne 0) {
      Write-Host ("NVT2 FAIL: {0} {1} exit={2}" -f $case.Id, $tf, $LASTEXITCODE)
      Write-Host 'Check NCA_NVT_HistoryExporter range/status; production Normal Run data is not used for NVT corpus replay.'
      exit $LASTEXITCODE
    }

    $payload = Get-Content -Raw -Path $out | ConvertFrom-Json
    $summary += [pscustomobject]@{
      source_id = $case.Id
      requested_cutoff = $case.Cutoff
      timeframe = $tf
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
  }
  Write-Host ''
}

$summaryPath = Join-Path $outputRoot 'NVT2_USDJPY_CORPUS_SUMMARY.json'
$summary | ConvertTo-Json -Depth 5 | Set-Content -Path $summaryPath -Encoding UTF8

Write-Host 'NVT2 USDJPY CORPUS CANDIDATE DUMP PASS'
Write-Host "Summary: $summaryPath"
Write-Host ''
Write-Host 'Important: teacher-video date cutoffs are provisional date-level upper bounds.'
Write-Host 'NVT5 will tighten each event to the exact verified market cutoff.'
Write-Host 'Production live_input, Normal Run snapshot/state, and MT4 NCA_DRAW__ objects were not modified.'
