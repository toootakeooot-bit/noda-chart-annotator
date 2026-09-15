param(
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$ownershipDir = Join-Path $outputRoot 'nvt6_ownership'
$identityDir = Join-Path $outputRoot 'nvt6_identity'
$compareDir = Join-Path $outputRoot 'nvt6_compare'
$replaySummary = Join-Path $outputRoot 'NVT5_USDJPY_REPLAY_SUMMARY.json'

$ownershipSummary = Join-Path $ownershipDir 'NVT6_STRUCTURE_OWNERSHIP_PREFLIGHT_SUMMARY.json'
if (!(Test-Path $ownershipSummary)) {
  Write-Host "NVT6 RESEARCH PREPARE FAIL: missing ownership preflight summary: $ownershipSummary"
  Write-Host 'Run setup\RUN_NVT6_PREFLIGHT_ALL.cmd or run_nvt6_structure_ownership_preflight.ps1 first.'
  exit 2
}
if (!(Test-Path $replaySummary)) {
  Write-Host "NVT6 RESEARCH PREPARE FAIL: missing NVT5 replay summary: $replaySummary"
  exit 2
}

New-Item -ItemType Directory -Force -Path $compareDir | Out-Null
New-Item -ItemType Directory -Force -Path $identityDir | Out-Null

Write-Host 'NVT6 RESEARCH PREPARE START'
Write-Host '1/2 Ownership comparison: GT_0005 / GT_0006 / GT_0007'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_ownership_comparison.py') `
  '--ownership-dir' $ownershipDir `
  '--output' (Join-Path $compareDir 'NVT6_OWNERSHIP_COMPARISON.json')
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 RESEARCH PREPARE STOPPED at ownership comparison exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host '2/2 Canonical candidate geometry view: GT_0003 / H4 source pair'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_canonical_candidate_view.py') `
  '--replay-summary' $replaySummary `
  '--source-id' 'NVT_VIDEO_20260830' `
  '--timeframe' 'H4' `
  '--output' (Join-Path $identityDir 'GT_0003_CANONICAL_CANDIDATE_VIEW.json')
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 RESEARCH PREPARE STOPPED at canonical candidate view exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT6 RESEARCH PREPARE PASS'
Write-Host ("Ownership comparison: {0}" -f (Join-Path $compareDir 'NVT6_OWNERSHIP_COMPARISON.json'))
Write-Host ("Canonical view: {0}" -f (Join-Path $identityDir 'GT_0003_CANONICAL_CANDIDATE_VIEW.json'))
Write-Host 'Research only. Structure Selector beta is still blocked from production.'
Write-Host 'Production Normal Run / NCA_DRAW__ / MT4 objects remain unchanged.'
