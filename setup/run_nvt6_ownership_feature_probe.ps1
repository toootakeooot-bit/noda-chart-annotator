param(
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$ownershipDir = Join-Path $outputRoot 'nvt6_ownership'
$identityDir = Join-Path $outputRoot 'nvt6_identity'
$featureDir = Join-Path $outputRoot 'nvt6_features'
$resolved = Join-Path $outputRoot 'NVT5_RESOLVED_CUTOFFS.json'
$replaySummary = Join-Path $outputRoot 'NVT5_USDJPY_REPLAY_SUMMARY.json'

if (!(Test-Path $resolved)) {
  Write-Host "NVT6 FEATURE PROBE FAIL: missing $resolved"
  exit 2
}
if (!(Test-Path $replaySummary)) {
  Write-Host "NVT6 FEATURE PROBE FAIL: missing $replaySummary"
  exit 2
}

$requiredPools = @(
  (Join-Path $ownershipDir 'NVT_VIDEO_20260912_H1_MICRO_DOW_POOL.json'),
  (Join-Path $ownershipDir 'NVT_VIDEO_20260808_H1_MICRO_DOW_POOL.json')
)
foreach ($p in $requiredPools) {
  if (!(Test-Path $p)) {
    Write-Host "NVT6 FEATURE PROBE FAIL: missing ownership pool: $p"
    Write-Host 'Run setup\RUN_NVT6_PREFLIGHT_ALL.cmd first.'
    exit 2
  }
}

New-Item -ItemType Directory -Force -Path $identityDir | Out-Null
New-Item -ItemType Directory -Force -Path $featureDir | Out-Null

Write-Host 'NVT6 OWNERSHIP FEATURE PROBE START'
Write-Host 'Research only. Production Normal Run / NCA_DRAW__ / MT4 remain untouched.'
Write-Host ''

Write-Host '1/2 Rebuild canonical candidate view with geometry/context separation (schema 0.2)'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_canonical_candidate_view.py') `
  '--replay-summary' $replaySummary `
  '--source-id' 'NVT_VIDEO_20260830' `
  '--timeframe' 'H4' `
  '--output' (Join-Path $identityDir 'GT_0003_CANONICAL_CANDIDATE_VIEW_V02.json')
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 FEATURE PROBE STOPPED at canonical v0.2 exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host '2/2 Probe GT_0006 positive vs GT_0007 timeframe-global NO-LINE features'
& $Python (Join-Path $RepoRoot 'tools\nvt\probe_ownership_features.py') `
  '--resolved-cutoffs' $resolved `
  '--ownership-dir' $ownershipDir `
  '--output' (Join-Path $featureDir 'NVT6_OWNERSHIP_FEATURE_PROBE.json')
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 FEATURE PROBE STOPPED at ownership feature probe exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT6 OWNERSHIP FEATURE PROBE PASS'
Write-Host ("Canonical v0.2: {0}" -f (Join-Path $identityDir 'GT_0003_CANONICAL_CANDIDATE_VIEW_V02.json'))
Write-Host ("Ownership features: {0}" -f (Join-Path $featureDir 'NVT6_OWNERSHIP_FEATURE_PROBE.json'))
Write-Host 'PASS means research evidence was generated. No production ownership rule is fixed yet.'
