param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$OutDir = Join-Path $Common 'live_output'
$Safe = ($Symbol -replace '[<>:"/\\|?*]', '_')

$Gate = Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_GATE_0919.json'
$Auto = Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_ADJUDICATION_0919_AUTO.json'
$Overrides = Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_OVERRIDES_0919.json'
$Final = Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_ADJUDICATION_0919_FINAL.json'
$V4 = Join-Path $OutDir 'NVT9_USDJPY_V4_VISIBILITY_DECISION_0919.json'
$Template = Join-Path $OutDir 'NVT9_USDJPY_V4_DISPLAY_DECISIONS_0919_TEMPLATE.json'
$Decisions = Join-Path $OutDir 'NVT9_USDJPY_V4_DISPLAY_DECISIONS_0919.json'
$Snapshot = Join-Path $OutDir ("NORMAL_{0}_live_snapshot.csv" -f $Safe)
$Preview = Join-Path $OutDir ("NORMAL_{0}_live_snapshot_V6_0919.csv" -f $Safe)
$Regression = Join-Path $OutDir 'NVT9_USDJPY_V5_VISIBILITY_REGRESSION_0919.json'

Write-Host 'NVT9 09/19 V4 -> V6 PREVIEW'
Write-Host '============================'
Write-Host 'Audit only. No Production or MT4 writeback.'
Write-Host ''

if (-not (Test-Path $Gate)) {
  Write-Host "FAIL: V3.5 gate not found: $Gate"
  exit 2
}
$GatePayload = Get-Content -Raw -Encoding UTF8 $Gate | ConvertFrom-Json
if ($GatePayload.status -ne 'PASS_V3_5') {
  Write-Host ("STOP: V3.5 status is {0}; V4/V6 cannot proceed." -f $GatePayload.status)
  exit 0
}

$Adjudication = $Auto
if ((Test-Path $Overrides) -and (Test-Path $Final)) { $Adjudication = $Final }

if (-not (Test-Path $V4)) {
  Write-Host "FAIL: V4 decision input not found: $V4"
  Write-Host 'Run RUN_NVT9_PHASE1_ADVANCE_0919.cmd first.'
  exit 3
}

Write-Host '[1/4] V4/V6 self-test'
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt9_v4_v6_preview.py')
if ($LASTEXITCODE -ne 0) { Write-Host "SELFTEST FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host ''
Write-Host '[2/4] Build explicit display-decision template'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_v4_display_template.py') --v4 $V4 --adjudication $Adjudication --output $Template
if ($LASTEXITCODE -ne 0) { Write-Host "DISPLAY TEMPLATE FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

if (-not (Test-Path $Decisions)) {
  Write-Host ''
  Write-Host 'STOP: explicit display decisions are not filled yet.'
  Write-Host ("Template: {0}" -f $Template)
  Write-Host 'Copy the template to NVT9_USDJPY_V4_DISPLAY_DECISIONS_0919.json and fill only visually confirmed decisions.'
  exit 0
}

if (-not (Test-Path $Snapshot)) {
  Write-Host "FAIL: Normal Run snapshot not found: $Snapshot"
  exit 4
}

Write-Host ''
Write-Host '[3/4] Build audit-only V6 preview'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_v6_visibility_preview.py') --snapshot $Snapshot --decisions $Decisions --output-dir $OutDir
if ($LASTEXITCODE -ne 0) { Write-Host "V6 PREVIEW FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host ''
Write-Host '[4/4] Run V5 teacher-invariant regression on V6 preview'
& $Python (Join-Path $RepoRoot 'tools\nvt\validate_nvt9_visibility_invariants.py') --preview $Preview --output $Regression
if ($LASTEXITCODE -ne 0) { Write-Host "V5 REGRESSION FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host ''
Write-Host 'V4/V5/V6 AUDIT PATH PASS'
Write-Host ("Preview:    {0}" -f $Preview)
Write-Host ("Regression: {0}" -f $Regression)
Write-Host 'No Production, Renderer, snapshot source, or NCA_DRAW__ writeback occurred.'
exit 0
