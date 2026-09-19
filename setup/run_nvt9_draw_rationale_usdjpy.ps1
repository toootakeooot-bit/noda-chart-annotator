param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$InputDir = Join-Path $Common 'live_input'
$OutputDir = Join-Path $Common 'live_output'

Write-Host 'NVT9 DRAW RATIONALE - USDJPY#'
Write-Host '============================'

& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_draw_rationale.py') --symbol $Symbol --input-dir $InputDir --output-dir $OutputDir
$code = $LASTEXITCODE
if ($code -ne 0) {
  Write-Host "NVT9 DRAW RATIONALE FAILED - exit=$code"
  exit $code
}

$safe = ($Symbol -replace '[<>:"/\\|?*]', '_')
Write-Host ''
Write-Host 'DRAW RATIONALE PASS'
Write-Host ("JSON: {0}" -f (Join-Path $OutputDir ("NVT9_{0}_draw_rationale.json" -f $safe)))
Write-Host ("CSV:  {0}" -f (Join-Path $OutputDir ("NVT9_{0}_draw_rationale.csv" -f $safe)))
Write-Host ("TXT:  {0}" -f (Join-Path $OutputDir ("NVT9_{0}_draw_rationale.txt" -f $safe)))
Write-Host ''
Write-Host 'Audit only: drawing and NCA_DRAW__ objects are unchanged.'
exit 0
