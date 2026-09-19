param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$OutDir = Join-Path $Common 'live_output'
$Safe = ($Symbol -replace '[<>:"/\\|?*]', '_')
$Snapshot = Join-Path $OutDir ("NORMAL_{0}_live_snapshot.csv" -f $Safe)
$Rule = Join-Path $RepoRoot 'nvt\manifests\NVT9_VISIBILITY_RULE_0919_H1_V01.json'

if (-not (Test-Path $Snapshot)) {
  Write-Host "FAIL: snapshot not found: $Snapshot"
  exit 2
}
if (-not (Test-Path $Rule)) {
  Write-Host "FAIL: visibility rule not found: $Rule"
  exit 3
}

Write-Host 'NVT9 09/19 VISIBILITY PREVIEW'
Write-Host '============================'
Write-Host 'Legacy H1 16->12 candidate only. It is blocked until V3.5 ownership is resolved.'
Write-Host 'Audit only. Production snapshot and renderer will not be changed.'
Write-Host ''

& $Python (Join-Path $RepoRoot 'tools\nvt\build_visibility_preview.py') --snapshot $Snapshot --rule $Rule --output-dir $OutDir
$code = $LASTEXITCODE
if ($code -eq 8) {
  Write-Host 'STOP: rule manifest is still blocked by V3.5 cross-TF ownership.'
  Write-Host 'Use RUN_NVT9_PHASE1_ADVANCE_0919.cmd instead.'
  exit 0
}
if ($code -ne 0) {
  Write-Host "VISIBILITY PREVIEW FAILED - exit=$code"
  exit $code
}

Write-Host ''
Write-Host 'Expected with current 16-row baseline:'
Write-Host '  D1 : 16'
Write-Host '  H4 : 16'
Write-Host '  H1 : 12'
Write-Host '  M15: 16'
Write-Host ''
Write-Host 'No MT4 drawing has been changed.'
exit 0
