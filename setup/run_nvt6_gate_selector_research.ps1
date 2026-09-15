param(
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$visibilityDir = Join-Path $outputRoot 'nvt6_visibility'
$featureDir = Join-Path $outputRoot 'nvt6_features'
$gateDir = Join-Path $outputRoot 'nvt6_gate'
$selectorDir = Join-Path $outputRoot 'nvt6_selector'

New-Item -ItemType Directory -Force -Path $visibilityDir | Out-Null
New-Item -ItemType Directory -Force -Path $gateDir | Out-Null
New-Item -ItemType Directory -Force -Path $selectorDir | Out-Null

Write-Host 'NVT6 GATE + SELECTOR RESEARCH START'
Write-Host 'Research only. Production Normal Run / NCA_DRAW__ / MT4 remain untouched.'
Write-Host ''

$gt5 = Join-Path $RepoRoot 'nvt\ground_truth\GT_0005.json'
$gt5Precheck = Join-Path $visibilityDir 'GT_0005_DISPLAY_SUPPRESSION_PRECHECK.json'
$featureProbe = Join-Path $featureDir 'NVT6_OWNERSHIP_FEATURE_PROBE.json'
$gateReport = Join-Path $gateDir 'NVT6_OWNERSHIP_GATE_HYPOTHESES.json'
$selectorReport = Join-Path $selectorDir 'GT_0006_SELECTOR_PRERANK.json'

Write-Host '1/4 Verify GT_0005 valid-but-display-suppressed semantics FIRST'
& $Python (Join-Path $RepoRoot 'tools\nvt\verify_gt0005_display_suppression.py') `
  '--ground-truth' $gt5 `
  '--output' $gt5Precheck
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 RESEARCH STOPPED at GT_0005 precheck exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host '2/4 Rebuild ownership feature probe for GT_0006 / GT_0007'
& (Join-Path $PSScriptRoot 'run_nvt6_ownership_feature_probe.ps1') -Python $Python
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 RESEARCH STOPPED at ownership feature probe exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}
if (!(Test-Path $featureProbe)) {
  Write-Host "NVT6 RESEARCH FAIL: feature probe missing: $featureProbe"
  exit 2
}

Write-Host ''
Write-Host '3/4 Compare Ownership Gate hypotheses A/B/C'
& $Python (Join-Path $RepoRoot 'tools\nvt\probe_ownership_gate_hypotheses.py') `
  '--feature-probe' $featureProbe `
  '--gt0005-precheck' $gt5Precheck `
  '--output' $gateReport
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 RESEARCH STOPPED at ownership gate probe exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host '4/4 Build GT_0006 selector pre-rank from Gate C survivors'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_gt0006_selector_prerank.py') `
  '--gate-report' $gateReport `
  '--output' $selectorReport
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 RESEARCH STOPPED at selector pre-rank exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT6 GATE + SELECTOR RESEARCH PASS'
Write-Host ("GT_0005 precheck: {0}" -f $gt5Precheck)
Write-Host ("Ownership gate hypotheses: {0}" -f $gateReport)
Write-Host ("GT_0006 selector pre-rank: {0}" -f $selectorReport)
Write-Host 'PASS means research evidence was generated. No production gate/selector rule is fixed.'
