param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$InputDir = Join-Path $Common 'live_input'
$OutDir = Join-Path $Common 'live_output'
$Safe = ($Symbol -replace '[<>:"/\\|?*]', '_')
$State = Join-Path $OutDir ("NORMAL_{0}_live_state.json" -f $Safe)
$Policy = Join-Path $RepoRoot 'nvt\manifests\NVT9_TF_DISPLAY_MAP_0919_V01.json'
$Contract = Join-Path $RepoRoot 'nvt\manifests\NVT9_PLAN_B_DISPLAY_CONTRACT_20260920.json'
$ContractAudit = Join-Path $OutDir 'NVT9_PLAN_B_DISPLAY_CONTRACT_AUDIT_0919.json'
$Preview = Join-Path $OutDir 'NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv'
$Audit = Join-Path $OutDir 'NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json'

Write-Host 'NVT9 09/19 TF DISPLAY MAP PREVIEW'
Write-Host '================================='
Write-Host 'Research only.'
Write-Host 'SOURCE GEOMETRY = ACTUAL NORMAL RUN LIVE STATE (same lines already shown on source charts).'
Write-Host 'PLAN B display direction: SOURCE TF -> SELF + ONE HIGHER CHART.'
Write-Host 'H4 structure -> H4 + D1; H1 structure -> H1 + H4; M15 structure -> M15 + H1.'
Write-Host 'Equivalent chart view: D1=D1+H4, H4=H4+H1, H1=H1+M15, M15=M15.'
Write-Host 'Structural owner remains the SOURCE timeframe.'
Write-Host 'Audit preview is CURRENT-only and nearest-only. Far context is disabled.'
Write-Host 'MT4 audit preview clears ALL chart objects on the current chart, then draws only the selected preview.'
Write-Host 'HL PREVIEW: always draw one provisional pink HL on each source chart; 38% remains Turn/reaction confirmation only.'
Write-Host ''

Write-Host '[0/4] Independent Plan B contract gate'
& $Python (Join-Path $RepoRoot 'tools\nvt\validate_nvt9_plan_b_contract.py') --contract $Contract --policy $Policy --output $ContractAudit
if ($LASTEXITCODE -ne 0) {
  Write-Host 'STOP: Plan B mapping does not match the frozen user-confirmed contract.'
  Write-Host ("Audit: {0}" -f $ContractAudit)
  exit $LASTEXITCODE
}
Write-Host 'PLAN B CONTRACT PASS'
Write-Host '  H4 structure -> H4 + D1'
Write-Host '  H1 structure -> H1 + H4'
Write-Host '  M15 structure -> M15 + H1'
Write-Host ''

Write-Host '[1/4] Self-tests'
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt9_deep_lifecycle_state.py')
if ($LASTEXITCODE -ne 0) { Write-Host "DEEP LIFECYCLE SELFTEST FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt9_tf_mapped_preview.py')
if ($LASTEXITCODE -ne 0) { Write-Host "TF MAP PREVIEW SELFTEST FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt9_tfmap_renderer_safety.py')
if ($LASTEXITCODE -ne 0) { Write-Host "TF MAP RENDERER SAFETY SELFTEST FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host ''
Write-Host '[2/4] Confirm actual NormalRun source state'
$Required=@('D1','H4','H1','M15') | ForEach-Object { Join-Path $InputDir ("NORMAL_{0}_{1}.csv" -f $Safe,$_) }
$Missing=@($Required | Where-Object { !(Test-Path $_) })
if ($Missing.Count -gt 0) {
  Write-Host 'STOP: NormalRun input files are missing.'
  $Missing | ForEach-Object { Write-Host ("  missing: {0}" -f $_) }
  exit 2
}
if (!(Test-Path $State)) {
  Write-Host 'STOP: NormalRun live state not found.'
  Write-Host ("Missing: {0}" -f $State)
  Write-Host 'Run the existing NormalRun process once before this preview.'
  exit 3
}
$StatePayload = Get-Content -Raw -Encoding UTF8 $State | ConvertFrom-Json
if ($StatePayload.schema -ne 'nca-live-state/1.0') {
  Write-Host 'STOP: NormalRun live state schema is invalid.'
  exit 4
}
Write-Host 'NORMAL RUN SOURCE STATE PASS'
Write-Host ("Source: {0}" -f $State)
Write-Host ''
Write-Host '[3/4] Source policy'
Write-Host 'The preview now reuses the ACTUAL NormalRun line geometry already used on each source chart.'
Write-Host 'No deep-history H4/H1 replacement geometry is used for this display-map test.'
Write-Host ''
Write-Host '[4/4] Build mapped preview snapshot'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_tf_mapped_preview.py') --state $State --policy $Policy --input-dir $InputDir --input-prefix NORMAL --output-dir $OutDir
if ($LASTEXITCODE -ne 0) { Write-Host "TF MAP PREVIEW BUILD FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

$AuditPayload = Get-Content -Raw -Encoding UTF8 $Audit | ConvertFrom-Json
Write-Host ''
Write-Host 'TF DISPLAY MAP PREVIEW PASS'
Write-Host ("Preview: {0}" -f $Preview)
Write-Host ("Audit:   {0}" -f $Audit)
Write-Host ''
Write-Host 'Selected family counts:'
Write-Host ("  D1 : {0}" -f $AuditPayload.selected_family_counts.D1)
Write-Host ("  H4 : {0}" -f $AuditPayload.selected_family_counts.H4)
Write-Host ("  H1 : {0}" -f $AuditPayload.selected_family_counts.H1)
Write-Host ("  M15: {0}" -f $AuditPayload.selected_family_counts.M15)
Write-Host ''
Write-Host 'Plan B source presence:'
Write-Host ("  D1 chart <- D1:{0} H4:{1}" -f $AuditPayload.selected_source_counts.D1.D1,$AuditPayload.selected_source_counts.D1.H4)
Write-Host ("  H4 chart <- H4:{0} H1:{1}" -f $AuditPayload.selected_source_counts.H4.H4,$AuditPayload.selected_source_counts.H4.H1)
Write-Host ("  H1 chart <- H1:{0} M15:{1}" -f $AuditPayload.selected_source_counts.H1.H1,$AuditPayload.selected_source_counts.H1.M15)
Write-Host ("  M15 chart <- M15:{0}" -f $AuditPayload.selected_source_counts.M15.M15)
Write-Host ''
Write-Host 'Current audit preview: nearest CURRENT family only from each assigned source TF.'
Write-Host 'Far context is disabled.'
Write-Host 'HL preview is always visible; HL break does NOT yet switch TL direction.'
Write-Host '38% is reaction/Turn confirmation only and is NOT used as the HL price.'
Write-Host 'MT4 audit mode clears all existing chart objects on the chart before drawing the preview.'
Write-Host ''
Write-Host 'Next MT4 step: install/compile NCA_NVT9_TFMap_Preview_Renderer.mq4 and run it on the charts you want to compare (especially H4 and M15).'
Write-Host 'Research objects use NVT9_TFMAP__ only.'
Write-Host 'Audit renderer intentionally deletes all existing MT4 chart objects on the chart before drawing.'
exit 0
