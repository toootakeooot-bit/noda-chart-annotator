param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$InputDir = Join-Path $Common 'nvt_input'
$OutDir = Join-Path $Common 'live_output'
$Safe = ($Symbol -replace '[<>:"/\\|?*]', '_')
$State = Join-Path $OutDir 'NVT9_USDJPY_DEEP_LIFECYCLE_STATE_0919.json'
$Policy = Join-Path $RepoRoot 'nvt\manifests\NVT9_TF_DISPLAY_MAP_0919_V01.json'
$Preview = Join-Path $OutDir 'NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv'
$Audit = Join-Path $OutDir 'NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json'

Write-Host 'NVT9 09/19 TF DISPLAY MAP PREVIEW'
Write-Host '================================='
Write-Host 'Research only.'
Write-Host 'PLAN B display direction: SOURCE TF -> SELF + ONE HIGHER CHART.'
Write-Host 'H4 structure -> H4 + D1; H1 structure -> H1 + H4; M15 structure -> M15 + H1.'
Write-Host 'Equivalent chart view: D1=D1+H4, H4=H4+H1, H1=H1+M15, M15=M15.'
Write-Host 'Structural owner remains the SOURCE timeframe.'
Write-Host 'Far redundant families are hidden; one farther higher-TF context may remain when direction is unclear.'
Write-Host ''

Write-Host '[1/4] Self-tests'
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt9_deep_lifecycle_state.py')
if ($LASTEXITCODE -ne 0) { Write-Host "DEEP LIFECYCLE SELFTEST FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt9_tf_mapped_preview.py')
if ($LASTEXITCODE -ne 0) { Write-Host "TF MAP PREVIEW SELFTEST FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt9_tfmap_renderer_safety.py')
if ($LASTEXITCODE -ne 0) { Write-Host "TF MAP RENDERER SAFETY SELFTEST FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host ''
Write-Host '[2/4] Confirm deep NVT history exists'
$Required=@('D1','H4','H1','M15') | ForEach-Object { Join-Path $InputDir ("NVT_{0}_{1}.csv" -f $Safe,$_) }
$Missing=@($Required | Where-Object { !(Test-Path $_) })
if ($Missing.Count -gt 0) {
  Write-Host 'STOP: deep NVT history files are missing.'
  Write-Host 'Run NCA_NVT_HistoryExporter in MT4 with BarsToExport=6000 first.'
  $Missing | ForEach-Object { Write-Host ("  missing: {0}" -f $_) }
  exit 2
}

Write-Host ''
Write-Host '[3/4] Deep lifecycle state'
$ReuseState = $false
if (Test-Path $State) {
  try {
    $StatePayload = Get-Content -Raw -Encoding UTF8 $State | ConvertFrom-Json
    $StateTime = (Get-Item $State).LastWriteTimeUtc
    $NewestInput = ($Required | ForEach-Object { (Get-Item $_).LastWriteTimeUtc } | Sort-Object -Descending | Select-Object -First 1)
    if (($StatePayload.research_status -eq 'PASS_DEEP_LIFECYCLE_STATE') -and ($StateTime -ge $NewestInput)) {
      $ReuseState = $true
    }
  } catch {
    $ReuseState = $false
  }
}

if ($ReuseState) {
  Write-Host 'CACHE PASS: existing deep lifecycle state is valid and newer than all NVT history inputs.'
  Write-Host ("Reuse: {0}" -f $State)
} else {
  Write-Host 'Cache miss/stale: rebuilding deep lifecycle state. This is the expensive step.'
  Write-Host 'Progress will be printed for D1 -> H4 -> H1 -> M15.'
  & $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_deep_lifecycle_state.py') --symbol $Symbol --input-dir $InputDir --output-dir $OutDir
  if ($LASTEXITCODE -ne 0) { Write-Host "DEEP LIFECYCLE BUILD FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }
}

Write-Host ''
Write-Host '[4/4] Build mapped preview snapshot'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_tf_mapped_preview.py') --state $State --policy $Policy --input-dir $InputDir --output-dir $OutDir
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
Write-Host 'The preview prioritizes families nearest current price.'
Write-Host 'A farther higher-TF family is retained only as directional context when the nearby set does not make direction clear.'
Write-Host ''
Write-Host 'Next MT4 step: install/compile NCA_NVT9_TFMap_Preview_Renderer.mq4 and run it on the charts you want to compare (especially H4 and M15).'
Write-Host 'Research objects use NVT9_TFMAP__ only.'
Write-Host 'Production NCA_DRAW__ and manual objects are untouched.'
exit 0
