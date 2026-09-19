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
$Adjudication = Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_ADJUDICATION_0919.json'
$Gate = Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_GATE_0919.json'

Write-Host 'NVT9 09/19 OWNERSHIP ADJUDICATION'
Write-Host '================================'
Write-Host 'Research only. Ambiguous lines remain visible.'
Write-Host ''

Write-Host '[1/3] Self-test'
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt9_ownership_adjudication.py')
if ($LASTEXITCODE -ne 0) {
  Write-Host "SELFTEST FAILED - exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host '[2/3] Build conservative adjudication'
if (-not (Test-Path $Matrix)) {
  Write-Host "FAIL: cross-TF matrix not found: $Matrix"
  Write-Host 'Run RUN_NVT9_CROSS_TF_0919.cmd first.'
  exit 2
}
& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_ownership_adjudication.py') --matrix $Matrix --policy $Policy --output-dir $OutDir
if ($LASTEXITCODE -ne 0) {
  Write-Host "ADJUDICATION BUILD FAILED - exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host '[3/3] Evaluate V3.5 gate'
& $Python (Join-Path $RepoRoot 'tools\nvt\evaluate_nvt9_ownership_gate.py') --adjudication $Adjudication --output $Gate
if ($LASTEXITCODE -ne 0) {
  Write-Host "GATE EVALUATION FAILED - exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'OWNERSHIP REVIEW COMPLETE'
Write-Host ("Adjudication: {0}" -f $Adjudication)
Write-Host ("Gate:         {0}" -f $Gate)
Write-Host ''
Write-Host 'If gate status is BLOCKED_V3_5, the remaining rows require teacher/manual adjudication.'
Write-Host 'No Production or MT4 drawing was changed.'
exit 0
