param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$InputDir = Join-Path $Common 'nvt_input'
$OutDir = Join-Path $Common 'live_output\nvt9_reference_0912'
$Policy = Join-Path $RepoRoot 'nvt\manifests\NVT9_TF_DISPLAY_MAP_0919_V01.json'
$Reference = Join-Path $RepoRoot 'nvt\manifests\NVT9_0919_REFERENCE_LINES_V01.json'
$RejectedLedger = Join-Path $RepoRoot 'nvt\manifests\NVT9_REJECTED_DRAW_LEDGER_V01.json'

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host 'NVT9 09/12 CURRENT AUDIT PREPARE'
Write-Host '==============================='
Write-Host 'Cutoff: 2026-09-12 00:00 exclusive'
Write-Host 'Window: last 600 closed bars per timeframe'
Write-Host 'Rules: current audit branch (D1 continuation, H1 native TL/HL, spaced zones, Updated CH)'
Write-Host 'Production: unchanged'
Write-Host ''

Write-Host '[1/3] Build no-lookahead 600-bar base'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_reference_0912.py') --input-dir $InputDir --output-dir $OutDir --policy $Policy --symbol $Symbol --cutoff '2026-09-12T00:00:00'
if ($LASTEXITCODE -ne 0) { Write-Host '09/12 BASE BUILD FAILED'; exit $LASTEXITCODE }

Write-Host ''
Write-Host '[2/3] Build current structural overlay at 09/12 cutoff'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_structural_overlay_0919.py') --input-dir $InputDir --reference $Reference --output-dir $OutDir --symbol $Symbol --cutoff '2026-09-12T00:00:00' --case-tag '0912'
if ($LASTEXITCODE -ne 0) { Write-Host '09/12 STRUCTURAL OVERLAY FAILED'; exit $LASTEXITCODE }

if (Test-Path $RejectedLedger) {
  Copy-Item -Force $RejectedLedger (Join-Path $OutDir 'NVT9_REJECTED_DRAW_LEDGER_V01.json')
}

$SummaryPath = Join-Path $OutDir 'NVT9_0912_CURRENT_SUMMARY.json'
$OverlayPath = Join-Path $OutDir 'NVT9_0919_STRUCTURAL_OVERLAY_AUDIT.json'
$Summary = Get-Content -Raw -Encoding UTF8 $SummaryPath | ConvertFrom-Json
$Overlay = Get-Content -Raw -Encoding UTF8 $OverlayPath | ConvertFrom-Json

Write-Host ''
Write-Host '09/12 CURRENT SUMMARY'
Write-Host '---------------------'
foreach ($tf in 'D1','H4','H1','M15') {
  $c = $Summary.input_coverage.$tf
  Write-Host ("{0}: bars={1} first={2} last={3}" -f $tf,$c.bar_count,$c.first_bar,$c.last_bar)
}
Write-Host ("D1 continuation: {0} reason={1}" -f $Overlay.d1_continuation.status,$Overlay.d1_continuation.reason_code)
Write-Host ("H1 native TL/HL: {0} reason={1}" -f $Overlay.h1_native_continuation.status,$Overlay.h1_native_continuation.reason_code)
Write-Host ("H1 zones:        {0} count={1}" -f $Overlay.h1_reaction_zones.status,$Overlay.h1_reaction_zones.zone_count)
Write-Host ("H1 Updated CH:   {0} reason={1}" -f $Overlay.h1_updated_ch.status,$Overlay.h1_updated_ch.reason_code)

Write-Host ''
Write-Host '[3/3] Install/compile MT4 viewers'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'install_nvt9_tfmap_preview_auto.ps1')
if ($LASTEXITCODE -ne 0) { Write-Host 'MT4 INSTALL FAILED'; exit $LASTEXITCODE }

Write-Host ''
Write-Host 'READY - 09/12 CURRENT DRAW'
Write-Host 'MT4 script: NCA_NVT9_AB_View'
Write-Host 'Set Case=2026-09-12, Variant=OLD (defaults are prepared for this audit).'
Write-Host 'The 09/12 OLD slot now reads the dedicated 600-bar base and current structural overlay.'
Write-Host 'Use NCA_NVT9_Return_Live to return to live charts.'
exit 0
