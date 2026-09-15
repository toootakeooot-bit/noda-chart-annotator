param(
  [string]$BrokerSymbol = 'USDJPY#',
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$inputDir = Join-Path $common 'live_input'
$outputRoot = Join-Path $common 'nvt_output'
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

function Safe-FileSymbol([string]$Value) {
  return ($Value -replace '[<>:"/\\|?*]', '_')
}

$safe = Safe-FileSymbol $BrokerSymbol
$tfs = @('D1','H4','H1','M15')

$required = $tfs | ForEach-Object {
  Join-Path $inputDir ("NORMAL_{0}_{1}.csv" -f $safe, $_)
}
$missing = @($required | Where-Object { !(Test-Path $_) })
if ($missing.Count -gt 0) {
  Write-Host 'NVT2 WAITING FOR USDJPY MT4 EXPORT'
  Write-Host "Run NCA_NormalRun_Exporter once on $BrokerSymbol first."
  Write-Host 'Missing:'
  $missing | ForEach-Object { Write-Host "  $_" }
  exit 2
}

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
Write-Host ''

foreach ($case in $cases) {
  $caseDir = Join-Path $outputRoot $case.Id
  New-Item -ItemType Directory -Force -Path $caseDir | Out-Null
  Write-Host ("CASE {0} cutoff<={1}" -f $case.Id, $case.Cutoff)

  foreach ($tf in $tfs) {
    $src = Join-Path $inputDir ("NORMAL_{0}_{1}.csv" -f $safe, $tf)
    $out = Join-Path $caseDir ("candidates_{0}_{1}.json" -f $safe, $tf)

    & $Python (Join-Path $RepoRoot 'tools\nvt\dump_candidates.py') `
      '--input-csv' $src `
      '--symbol' $BrokerSymbol `
      '--timeframe' $tf `
      '--cutoff' $case.Cutoff `
      '--output' $out

    if ($LASTEXITCODE -ne 0) {
      Write-Host ("NVT2 FAIL: {0} {1} exit={2}" -f $case.Id, $tf, $LASTEXITCODE)
      exit $LASTEXITCODE
    }

    $payload = Get-Content -Raw -Path $out | ConvertFrom-Json
    $summary += [pscustomobject]@{
      source_id = $case.Id
      requested_cutoff = $case.Cutoff
      timeframe = $tf
      broker_symbol = $BrokerSymbol
      effective_last_closed_bar = $payload.effective_last_closed_bar
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
Write-Host 'Important: 23:59:59 is only a date-level upper bound. Each JSON records the actual last broker bar <= cutoff in effective_last_closed_bar.'
Write-Host 'No Normal Run snapshot/state or MT4 drawing objects were modified.'
