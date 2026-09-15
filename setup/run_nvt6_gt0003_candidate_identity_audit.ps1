param(
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$summary = Join-Path $outputRoot 'NVT5_USDJPY_REPLAY_SUMMARY.json'
$outDir = Join-Path $outputRoot 'nvt6_identity'
$out = Join-Path $outDir 'GT_0003_CANDIDATE_IDENTITY_AUDIT.json'

if (!(Test-Path $summary)) {
  Write-Host "NVT6 FAIL: missing NVT5 replay summary: $summary"
  exit 2
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Host 'NVT6 P2: GT_0003 CANDIDATE IDENTITY AUDIT'
Write-Host 'Research only; production candidate identity is not changed.'
Write-Host ''

& $Python (Join-Path $RepoRoot 'tools\nvt\audit_candidate_identity.py') `
  '--replay-summary' $summary `
  '--source-id' 'NVT_VIDEO_20260830' `
  '--timeframe' 'H4' `
  '--output' $out

if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 GT_0003 CANDIDATE IDENTITY AUDIT FAILED exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT6 GT_0003 CANDIDATE IDENTITY AUDIT PASS'
Write-Host "Report: $out"
Write-Host 'PASS means the collision report was generated; it does not change production identity semantics.'
