param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$InputDir = Join-Path $Common 'nvt_input'
$LiveOutput = Join-Path $Common 'live_output'
$RefOut = Join-Path $LiveOutput 'nvt9_reference_0919'
$DiagOut = Join-Path $RefOut 'diagnostic'
$Manifest = Join-Path $RepoRoot 'nvt\manifests\NVT9_0919_REFERENCE_LINES_V01.json'
$RejectedLedger = Join-Path $RepoRoot 'nvt\manifests\NVT9_REJECTED_DRAW_LEDGER_V01.json'
$PreviewAudit = Join-Path $LiveOutput 'nvt9_ab_0912_0919\20260919\OLD\output\NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json'
$Safe = ($Symbol -replace '[<>:"/\\|?*]','_')

Write-Host 'NVT9 09/19 REFERENCE RESTORE + STAGE DIAGNOSTIC'
Write-Host '================================================'
Write-Host 'Audit: ID10IQ200'
Write-Host 'Reference: frozen 8 source-TF line families saved on 2026-09-19'
Write-Host ''

$Required = @('D1','H4','H1','M15') | ForEach-Object {
  Join-Path $InputDir ("NVT_{0}_{1}.csv" -f $Safe,$_)
}
$Missing = @($Required | Where-Object { !(Test-Path $_) })
if ($Missing.Count -gt 0) {
  Write-Host 'STOP: deep NVT inputs are missing.'
  Write-Host 'Run NCA_NVT_HistoryExporter once in MT4 with BarsToExport=6000, then rerun this CMD.'
  $Missing | ForEach-Object { Write-Host ("  missing: {0}" -f $_) }
  exit 2
}

New-Item -ItemType Directory -Force -Path $RefOut | Out-Null
New-Item -ItemType Directory -Force -Path $DiagOut | Out-Null
if (Test-Path $RejectedLedger) {
  Copy-Item -Force $RejectedLedger (Join-Path $RefOut 'NVT9_REJECTED_DRAW_LEDGER_V01.json')
}

Write-Host '[1/5] Rebuild current 09/19 OLD replay with selector audit'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'run_nvt9_ab_0912_0919.ps1') -Python $Python -Symbol $Symbol
if ($LASTEXITCODE -ne 0) { Write-Host 'CURRENT 09/19 REPLAY FAILED'; exit $LASTEXITCODE }
if (!(Test-Path $PreviewAudit)) { Write-Host ("STOP: preview audit not found: {0}" -f $PreviewAudit); exit 3 }

Write-Host ''
Write-Host '[2/5] Compare R0919-01..08 through 600-bar and deep A/B/C/D/E stages'
& $Python (Join-Path $RepoRoot 'tools\nvt\diagnose_nvt9_reference_0919.py') --input-dir $InputDir --reference $Manifest --output-dir $DiagOut --preview-audit $PreviewAudit --symbol $Symbol
if ($LASTEXITCODE -ne 0) { Write-Host 'DIAGNOSTIC FAILED'; exit $LASTEXITCODE }

$DiagPath = Join-Path $DiagOut 'NVT9_0919_REFERENCE_DIAGNOSTIC.json'
if (!(Test-Path $DiagPath)) { Write-Host ("STOP: diagnostic missing: {0}" -f $DiagPath); exit 4 }

Write-Host ''
Write-Host '[3/5] Build selected 09/19 reference families + decision HL + reason links'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_0919_reference.py') --manifest $Manifest --diagnostic $DiagPath --output-dir $RefOut
if ($LASTEXITCODE -ne 0) { Write-Host 'REFERENCE BUILD FAILED'; exit $LASTEXITCODE }

$Diag = Get-Content -Raw -Encoding UTF8 $DiagPath | ConvertFrom-Json

$IndexPath = Join-Path $RefOut 'NVT9_0919_REFERENCE_INDEX.json'
if (!(Test-Path $IndexPath)) { Write-Host ("STOP: reference index missing: {0}" -f $IndexPath); exit 5 }
$Index = Get-Content -Raw -Encoding UTF8 $IndexPath | ConvertFrom-Json

Write-Host ''
Write-Host 'HL RECOVERY SUMMARY'
Write-Host '-------------------'
Write-Host ("Recovered HL: {0}/{1}" -f $Index.hl_recovered_count,$Index.reference_count)
if ($Index.hl_pending_count -gt 0) {
  Write-Host ("Pending HL:   {0}" -f (($Index.hl_pending_reference_ids) -join ', '))
  Write-Host 'Pending means TL/CH restoration continues; HL is not guessed.'
}

Write-Host ''
Write-Host 'FIRST-DIVERGENCE SUMMARY'
Write-Host '------------------------'
foreach ($r in $Diag.results) {
  Write-Host ("{0}  {1,-3} {2,-9} -> {3}" -f $r.reference_id,$r.timeframe,$r.structure_level,$r.first_divergence_stage)
  Write-Host ("    {0}" -f $r.reason)
}

Write-Host ''
Write-Host '09/19 DISPLAY-SELECTION SUMMARY'
Write-Host '-------------------------------'
Write-Host ("Frozen display candidates: {0}" -f (($Diag.production_600_display_selected_refs) -join ', '))
Write-Host ("Actually drawn after overrides: {0}" -f (($Index.selected_reference_ids) -join ', '))
if ($Index.suppressed_reference_ids.Count -gt 0) {
  Write-Host ("Suppressed by audit decision: {0}" -f (($Index.suppressed_reference_ids) -join ', '))
}
foreach ($r in $Diag.results) {
  $p = $r.production_600_replay
  if ($null -ne $p -and $p.display_selected -eq $true) {
    Write-Host ("{0}: selector={1} display={2}" -f $r.reference_id,$p.selector_reason,$p.display_reason)
  }
}

Write-Host ''
Write-Host 'INPUT COVERAGE'
Write-Host '--------------'
foreach ($tf in @('D1','H4','H1','M15')) {
  $c = $Diag.input_coverage.$tf
  if ($null -ne $c) {
    Write-Host ("{0}: bars={1} first={2} last={3}" -f $tf,$c.replay_bar_count,$c.first_replay_bar,$c.last_replay_bar)
  }
}

Write-Host ''
Write-Host '[4/5] Build research structural overlay: D1 continuation TL/HL + H1 zones + Updated CH'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_structural_overlay_0919.py') --input-dir $InputDir --reference $Manifest --output-dir $RefOut --symbol $Symbol
if ($LASTEXITCODE -ne 0) { Write-Host 'STRUCTURAL OVERLAY BUILD FAILED'; exit $LASTEXITCODE }

$OverlayAuditPath = Join-Path $RefOut 'NVT9_0919_STRUCTURAL_OVERLAY_AUDIT.json'
if (!(Test-Path $OverlayAuditPath)) { Write-Host ("STOP: structural overlay audit missing: {0}" -f $OverlayAuditPath); exit 6 }
$OverlayAudit = Get-Content -Raw -Encoding UTF8 $OverlayAuditPath | ConvertFrom-Json

Write-Host ''
Write-Host 'STRUCTURAL OVERLAY SUMMARY'
Write-Host '--------------------------'
Write-Host ("D1 continuation TL/HL: {0} reason={1}" -f $OverlayAudit.d1_continuation.status,$OverlayAudit.d1_continuation.reason_code)
if ($OverlayAudit.d1_continuation.status -eq 'BUILT') {
  Write-Host ("  A1={0} {1}  A2={2} {3}" -f $OverlayAudit.d1_continuation.anchor1.time,$OverlayAudit.d1_continuation.anchor1.price,$OverlayAudit.d1_continuation.anchor2.time,$OverlayAudit.d1_continuation.anchor2.price)
  Write-Host ("  HL={0} {1} break={2}" -f $OverlayAudit.d1_continuation.decision_hl.time,$OverlayAudit.d1_continuation.decision_hl.price,$OverlayAudit.d1_continuation.decision_hl.break_time)
}
Write-Host ("H1 reaction zones: {0} count={1}" -f $OverlayAudit.h1_reaction_zones.status,$OverlayAudit.h1_reaction_zones.zone_count)
Write-Host ("H1 updated CH:     {0} reason={1}" -f $OverlayAudit.h1_updated_ch.status,$OverlayAudit.h1_updated_ch.reason_code)

Write-Host ''
Write-Host '[5/5] Install/compile numbered reference viewer'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'install_nvt9_tfmap_preview_auto.ps1')
if ($LASTEXITCODE -ne 0) { Write-Host 'VIEWER INSTALL FAILED'; exit $LASTEXITCODE }

Write-Host ''
Write-Host 'READY - 09/19 FROZEN REFERENCE RESTORED'
Write-Host '---------------------------------------'
Write-Host 'MT4 script: NCA_NVT9_Reference0919_View'
Write-Host 'Reference IDs: machine-selected subset of R0919-01 ... R0919-08'
Write-Host 'Each selected reference includes selector/display reason links.'
Write-Host 'Decision HL is drawn only when historical evidence is recovered; otherwise the Rxx-HL ID remains PENDING in the index.'
Write-Host ("Reference index: {0}" -f (Join-Path $RefOut 'NVT9_0919_REFERENCE_INDEX.txt'))
Write-Host ("Diagnostic:      {0}" -f (Join-Path $DiagOut 'NVT9_0919_REFERENCE_DIAGNOSTIC.txt'))
Write-Host ''
Write-Host 'Run the viewer once with USDJPY# D1/H4/H1/M15 open.'
Write-Host 'Reference + research overlay objects are replaced; manual objects and Production NCA_DRAW__ are preserved.'
Write-Host ("Structural overlay audit: {0}" -f (Join-Path $RefOut 'NVT9_0919_STRUCTURAL_OVERLAY_AUDIT.txt'))
Write-Host ("Rejected draw ledger:    {0}" -f (Join-Path $RefOut 'NVT9_REJECTED_DRAW_LEDGER_V01.json'))
exit 0
