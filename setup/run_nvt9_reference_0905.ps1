param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$InputDir = Join-Path $Common 'nvt_input'
$OutDir = Join-Path $Common 'live_output\nvt9_reference_0905'
$Policy = Join-Path $RepoRoot 'nvt\manifests\NVT9_TF_DISPLAY_MAP_0919_V01.json'
$Reference = Join-Path $RepoRoot 'nvt\manifests\NVT9_0919_REFERENCE_LINES_V01.json'
$RejectedLedger = Join-Path $RepoRoot 'nvt\manifests\NVT9_REJECTED_DRAW_LEDGER_V01.json'
$VisualTruth = Join-Path $RepoRoot 'nvt\manifests\NVT9_0905_VISUAL_TRUTH_V01.json'

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host 'NVT9 09/05 CURRENT AUDIT PREPARE'
Write-Host '==============================='
Write-Host 'Cutoff: 2026-09-05 00:00 exclusive'
Write-Host 'Window: last 600 closed bars per timeframe'
Write-Host 'Mode: first 09/05 visual audit; no 09/12-specific source suppression'
Write-Host 'Production: unchanged'
Write-Host ''

Write-Host '[1/4] Build no-lookahead 600-bar base'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_reference_0905.py') --input-dir $InputDir --output-dir $OutDir --policy $Policy --reference-manifest $Reference --symbol $Symbol --cutoff '2026-09-05T00:00:00'
if ($LASTEXITCODE -ne 0) { Write-Host '09/05 BASE BUILD FAILED'; exit $LASTEXITCODE }

Write-Host ''
Write-Host '[2/4] Build structural overlay at 09/05 cutoff'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_structural_overlay_0919.py') --input-dir $InputDir --reference $Reference --output-dir $OutDir --symbol $Symbol --cutoff '2026-09-05T00:00:00' --case-tag '0905' --visual-truth $VisualTruth
if ($LASTEXITCODE -ne 0) { Write-Host '09/05 STRUCTURAL OVERLAY FAILED'; exit $LASTEXITCODE }

if (Test-Path $RejectedLedger) { Copy-Item -Force $RejectedLedger (Join-Path $OutDir 'NVT9_REJECTED_DRAW_LEDGER_V01.json') }
Copy-Item -Force $VisualTruth (Join-Path $OutDir 'NVT9_0905_VISUAL_TRUTH_V01.json')

$SummaryPath = Join-Path $OutDir 'NVT9_0905_CURRENT_SUMMARY.json'
$OverlayPath = Join-Path $OutDir 'NVT9_0919_STRUCTURAL_OVERLAY_AUDIT.json'
$BaseAuditPath = Join-Path $OutDir 'base\NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json'
$Summary = Get-Content -Raw -Encoding UTF8 $SummaryPath | ConvertFrom-Json
$Overlay = Get-Content -Raw -Encoding UTF8 $OverlayPath | ConvertFrom-Json
$BaseAudit = Get-Content -Raw -Encoding UTF8 $BaseAuditPath | ConvertFrom-Json

Write-Host ''
Write-Host '09/05 CURRENT SUMMARY'
Write-Host '---------------------'
foreach ($tf in 'D1','H4','H1','M15') {
  $c = $Summary.input_coverage.$tf
  Write-Host ("{0}: bars={1} first={2} last={3}" -f $tf,$c.bar_count,$c.first_bar,$c.last_bar)
}
Write-Host ("Empty source TFs: {0}" -f (($BaseAudit.empty_source_tfs) -join ', '))
if ($BaseAudit.source_selection.H4.Count -gt 0) {
  $h4 = $BaseAudit.source_selection.H4[0]
  Write-Host ("H4 source: {0} role={1} reason={2} display={3} ref={4}" -f $h4.line_id,$h4.generation_role,$h4.display_reason,(($h4.display_roles) -join '/'),$h4.reference_id)
} else { Write-Host 'H4 source: NO-LINE at 09/05 previsual replay' }
if ($BaseAudit.source_selection.H1.Count -gt 0) {
  $h1 = $BaseAudit.source_selection.H1[0]
  Write-Host ("H1 source: {0} role={1} reason={2} ref={3}" -f $h1.line_id,$h1.generation_role,$h1.display_reason,$h1.reference_id)
} else { Write-Host 'H1 source: NO-LINE at 09/05 previsual replay' }
if ($BaseAudit.source_selection.M15.Count -gt 0) {
  $m15 = $BaseAudit.source_selection.M15[0]
  Write-Host ("M15 main roles: {0} display={1}" -f $m15.line_id,(($m15.display_roles) -join '/'))
}
Write-Host ("D1 approved truth: {0} reason={1}" -f $Overlay.d1_visual_truth.status,$Overlay.d1_visual_truth.reason_code)
if ($Overlay.d1_visual_truth.status -eq 'BUILT') {
  Write-Host ("  APPROVED D1 A1={0} {1}" -f $Overlay.d1_visual_truth.anchor1.time,$Overlay.d1_visual_truth.anchor1.price)
  Write-Host ("  APPROVED D1 A2={0} {1}" -f $Overlay.d1_visual_truth.anchor2.time,$Overlay.d1_visual_truth.anchor2.price)
  Write-Host ("  TL break={0} lifecycle={1}" -f $Overlay.d1_visual_truth.tl_break_time,$Overlay.d1_visual_truth.lifecycle_status)
}
Write-Host ("H1 native TL/HL: {0} reason={1}" -f $Overlay.h1_native_continuation.status,$Overlay.h1_native_continuation.reason_code)
Write-Host ("H1 zones: {0} count={1}" -f $Overlay.h1_reaction_zones.status,$Overlay.h1_reaction_zones.zone_count)
Write-Host ("H1 Updated CH: {0} reason={1}" -f $Overlay.h1_updated_ch.status,$Overlay.h1_updated_ch.reason_code)

Write-Host ''
Write-Host '[3/4] Verify 09/05 no-lookahead package before visual adjudication'
& $Python (Join-Path $RepoRoot 'tools\nvt\verify_nvt9_0905_previsual.py') --truth $VisualTruth --summary $SummaryPath --overlay-audit (Join-Path $OutDir 'NVT9_0919_STRUCTURAL_OVERLAY_AUDIT.json') --overlay-csv (Join-Path $OutDir 'NVT9_0919_STRUCTURAL_OVERLAY.csv') --base-audit (Join-Path $OutDir 'base\NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json') --base-csv (Join-Path $OutDir 'base\NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv')
if ($LASTEXITCODE -ne 0) { Write-Host '09/05 PREVISUAL VERIFY FAILED'; exit $LASTEXITCODE }

Write-Host ''
Write-Host '[4/4] Install/compile MT4 viewers'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'install_nvt9_tfmap_preview_auto.ps1')
if ($LASTEXITCODE -ne 0) { Write-Host 'MT4 INSTALL FAILED'; exit $LASTEXITCODE }

Write-Host ''
Write-Host 'READY - 09/05 FIRST VISUAL AUDIT'
Write-Host 'MT4 script: NCA_NVT9_AB_View'
Write-Host 'Set Case=2026-09-05, Variant=OLD.'
Write-Host '09/05-specific visual truth is not frozen yet; compare the four charts and annotate wrong/missing lines.'
Write-Host 'Use NCA_NVT9_Return_Live to return to live charts.'
exit 0
