param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$InputDir = Join-Path $Common 'nvt_input'
$LiveOut = Join-Path $Common 'live_output'
$HistoryRoot = Join-Path $LiveOut 'nvt9_history_4w_0919'
$Policy = Join-Path $RepoRoot 'nvt\manifests\NVT9_TF_DISPLAY_MAP_0919_V01.json'

Write-Host 'NVT9 4-WEEK HISTORICAL REPLAY'
Write-Host '============================='
Write-Host 'Baseline: 2026-09-19 approved visual state'
Write-Host 'Cases: 2026-08-22, 2026-08-29, 2026-09-05, 2026-09-12'
Write-Host 'Source: NVT deep-history export (not the 600-bar NormalRun export).'
Write-Host 'Rule: only MT4 bars strictly before each Saturday cutoff are used.'
Write-Host ''

& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_historical_4w.py') --input-dir $InputDir --input-prefix NVT --output-dir $HistoryRoot --policy $Policy --symbol $Symbol
if ($LASTEXITCODE -ne 0) {
  Write-Host ''
  Write-Host "NVT9 4-WEEK HISTORY BUILD FAILED - exit=$LASTEXITCODE"
  if ($LASTEXITCODE -eq 4) {
    Write-Host 'Required action: in MT4 run NCA_NVT_HistoryExporter once with BarsToExport=6000 or more.'
    Write-Host 'Then run the same PREPARE_NVT9_HISTORY_AUDIT.cmd again.'
  }
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT9 4-WEEK HISTORY BUILD PASS'
Write-Host ("Output: {0}" -f $HistoryRoot)
Write-Host 'Newest historical case can be activated with:'
Write-Host '  setup\ACTIVATE_NVT9_HISTORY_CASE.cmd 20260912'
