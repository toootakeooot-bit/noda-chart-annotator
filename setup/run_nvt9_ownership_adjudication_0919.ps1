param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$OutDir = Join-Path $Common 'live_output'
$Matrix = Join-Path $OutDir 'NVT9_USDJPY_CROSS_TF_0919.json'
$Policy = Join-Path $RepoRoot 'nvt\manifests\NVT9_OWNERSHIP_ADJUDICATION_POLICY_0919_V01.json'
$Auto = Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_ADJUDICATION_0919_AUTO.json'
$Template = Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_OVERRIDES_0919_TEMPLATE.json'
$Overrides = Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_OVERRIDES_0919.json'
$Final = Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_ADJUDICATION_0919_FINAL.json'
$Gate = Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_GATE_0919.json'

Write-Host 'NVT9 09/19 OWNERSHIP ADJUDICATION'
Write-Host '================================'
Write-Host 'Research only. Ambiguous lines remain visible.'
Write-Host ''

Write-Host '[1/4] Self-test'
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt9_ownership_adjudication.py')
if ($LASTEXITCODE -ne 0) { Write-Host "SELFTEST FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host ''
Write-Host '[2/4] Build conservative auto adjudication'
if (-not (Test-Path $Matrix)) {
  Write-Host "FAIL: cross-TF matrix not found: $Matrix"
  Write-Host 'Run RUN_NVT9_CROSS_TF_0919.cmd first.'
  exit 2
}
& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_ownership_adjudication.py') --matrix $Matrix --policy $Policy --output-dir $OutDir
if ($LASTEXITCODE -ne 0) { Write-Host "AUTO ADJUDICATION FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host ''
Write-Host '[3/4] Apply explicit overrides when present'
$AdjudicationForGate = $Auto
if (Test-Path $Overrides) {
  & $Python (Join-Path $RepoRoot 'tools\nvt\apply_nvt9_ownership_overrides.py') --auto $Auto --overrides $Overrides --output $Final
  if ($LASTEXITCODE -ne 0) { Write-Host "OVERRIDE MERGE FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }
  $AdjudicationForGate = $Final
} else {
  Write-Host 'No filled override file found. Auto adjudication will be evaluated.'
  Write-Host ("Template: {0}" -f $Template)
}

Write-Host ''
Write-Host '[4/4] Evaluate V3.5 gate'
& $Python (Join-Path $RepoRoot 'tools\nvt\evaluate_nvt9_ownership_gate.py') --adjudication $AdjudicationForGate --output $Gate
if ($LASTEXITCODE -ne 0) { Write-Host "GATE EVALUATION FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host ''
Write-Host 'OWNERSHIP REVIEW COMPLETE'
Write-Host ("Auto:     {0}" -f $Auto)
Write-Host ("Template: {0}" -f $Template)
if (Test-Path $Overrides) { Write-Host ("Final:    {0}" -f $Final) }
Write-Host ("Gate:     {0}" -f $Gate)
Write-Host ''
Write-Host 'BLOCKED_V3_5 means remaining non-exact rows need explicit teacher/manual adjudication.'
Write-Host 'No Production or MT4 drawing was changed.'
exit 0
