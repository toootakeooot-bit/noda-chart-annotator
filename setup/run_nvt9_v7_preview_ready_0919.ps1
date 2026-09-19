param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#',
  [string]$DataFolder = '',
  [string]$TerminalRoot = ''
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$OutDir = Join-Path $Common 'live_output'
$Safe = ($Symbol -replace '[<>:"/\\|?*]', '_')

$V6Audit = Join-Path $OutDir ("NORMAL_{0}_live_snapshot_V6_0919_audit.json" -f $Safe)
$V5 = Join-Path $OutDir 'NVT9_USDJPY_V5_VISIBILITY_REGRESSION_0919.json'
$Ready = Join-Path $OutDir 'NVT9_USDJPY_V7_PREVIEW_READY_0919.json'

Write-Host 'NVT9 09/19 V7 PREVIEW READY'
Write-Host '==========================='
Write-Host 'Research preview only. Production NCA_DRAW__ remains untouched.'
Write-Host ''

Write-Host '[1/3] Preview renderer safety self-test'
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt9_preview_renderer_safety.py')
if ($LASTEXITCODE -ne 0) { Write-Host "RENDERER SAFETY SELFTEST FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host ''
Write-Host '[2/3] Prepare V7 readiness audit'
if (-not (Test-Path $V6Audit)) { Write-Host "FAIL: V6 audit not found: $V6Audit"; exit 2 }
if (-not (Test-Path $V5)) { Write-Host "FAIL: V5 regression not found: $V5"; exit 3 }

& $Python (Join-Path $RepoRoot 'tools\nvt\prepare_nvt9_v7_preview_ready.py') --v6-audit $V6Audit --v5-regression $V5 --output $Ready
if ($LASTEXITCODE -ne 0) { Write-Host "V7 READY CHECK FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host ''
Write-Host '[3/3] Optional preview renderer install'
if ($DataFolder -ne '') {
  & (Join-Path $PSScriptRoot 'install_nvt9_preview_renderer.ps1') -DataFolder $DataFolder -TerminalRoot $TerminalRoot
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
  Write-Host 'DataFolder not supplied; install step skipped.'
  Write-Host 'Use setup\install_nvt9_preview_renderer.ps1 with your MT4 DataFolder when ready.'
}

Write-Host ''
Write-Host 'READY FOR V7 MT4 PREVIEW'
Write-Host ("Audit: {0}" -f $Ready)
Write-Host 'Run NCA_NVT9_Preview_Renderer once on USDJPY# D1/H4/H1/M15 and capture screenshots.'
Write-Host 'Preview objects use NVT9_PREVIEW__ only; Production NCA_DRAW__ and manual objects are untouched.'
exit 0
