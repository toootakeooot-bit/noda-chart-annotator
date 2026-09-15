param(
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$resolved = Join-Path $outputRoot 'NVT5_RESOLVED_CUTOFFS.json'
$gtDir = Join-Path $RepoRoot 'nvt\ground_truth'
$outDir = Join-Path $outputRoot 'nvt6_ownership'

if (!(Test-Path $resolved)) {
  Write-Host "NVT6 FAIL: missing NVT5 resolved cutoff file: $resolved"
  Write-Host 'Run NVT5 USDJPY replays first.'
  exit 2
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Host 'NVT6 P0/P1: STRUCTURE OWNERSHIP PREFLIGHT'
Write-Host 'Cases: GT_0005 / GT_0006 / GT_0007'
Write-Host 'Production Normal Run is not modified.'
Write-Host ''

& $Python (Join-Path $RepoRoot 'tools\nvt\run_structure_ownership_batch.py') `
  '--ground-truth-dir' $gtDir `
  '--resolved-cutoffs' $resolved `
  '--output-dir' $outDir `
  '--lookback-bars' '360'

if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 STRUCTURE OWNERSHIP PREFLIGHT FAILED exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT6 STRUCTURE OWNERSHIP PREFLIGHT PASS'
Write-Host ("Summary: {0}" -f (Join-Path $outDir 'NVT6_STRUCTURE_OWNERSHIP_PREFLIGHT_SUMMARY.json'))
Write-Host 'PASS means evidence was generated; it does NOT mean an ownership rule is production-ready.'
Write-Host 'GT_0005 / GT_0007 remain mandatory H1 NO-LINE negative controls.'
