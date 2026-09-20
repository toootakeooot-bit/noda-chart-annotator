param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$InputDir = Join-Path $Common 'nvt_input'
$OutputDir = Join-Path $Common 'live_output\nvt9_ab_0912_0919'
$Policy = Join-Path $RepoRoot 'nvt\manifests\NVT9_TF_DISPLAY_MAP_0919_V01.json'

Write-Host 'NVT9 OLD / NEW A-B AUDIT'
Write-Host '========================'
Write-Host 'OLD: frozen 09/19 selector/lifecycle emulation'
Write-Host 'NEW: regime-gated direction-switch ACTIVE-N V0.2'
Write-Host '     same-direction continuation does not replace the main TL'
Write-Host '     opposite switch must be formed after the current active anchor2'
Write-Host 'Colors: unchanged from 09/19'
Write-Host 'Plan B: unchanged'
Write-Host 'Cases: 2026-09-12 and 2026-09-19'
Write-Host ''

& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_ab_0912_0919.py') --input-dir $InputDir --output-dir $OutputDir --policy $Policy --symbol $Symbol

if ($LASTEXITCODE -ne 0) {
  Write-Host ''
  Write-Host "NVT9 A-B BUILD FAILED - exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT9 A-B BUILD PASS'
Write-Host ("Summary: {0}" -f (Join-Path $OutputDir 'AB_0912_0919_SUMMARY.json'))