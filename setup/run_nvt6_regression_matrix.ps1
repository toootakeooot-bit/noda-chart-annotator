param(
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$visibilityDir = Join-Path $outputRoot 'nvt6_visibility'
$gateDir = Join-Path $outputRoot 'nvt6_gate'
$clusterDir = Join-Path $outputRoot 'nvt6_cluster'
$selectorDir = Join-Path $outputRoot 'nvt6_selector'
$identityDir = Join-Path $outputRoot 'nvt6_identity'
$regressionDir = Join-Path $outputRoot 'nvt6_regression'

$required = @(
  (Join-Path $visibilityDir 'GT_0005_DISPLAY_SUPPRESSION_PRECHECK.json'),
  (Join-Path $gateDir 'NVT6_OWNERSHIP_GATE_HYPOTHESES.json'),
  (Join-Path $clusterDir 'GT_0006_CLUSTER_RIGHT_EDGE_PROBE.json'),
  (Join-Path $selectorDir 'GT_0006_SELECTOR_BETA_RESEARCH.json'),
  (Join-Path $identityDir 'GT_0003_CANONICAL_CANDIDATE_VIEW_V02.json')
)
foreach ($p in $required) {
  if (!(Test-Path $p)) {
    Write-Host "NVT6 REGRESSION MATRIX FAIL: missing $p"
    exit 2
  }
}

New-Item -ItemType Directory -Force -Path $regressionDir | Out-Null

Write-Host 'NVT6 SOFT REGRESSION MATRIX START'
Write-Host 'Research only. No production writeback / MT4 drawing.'

& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt6_regression_matrix.py') `
  '--ground-truth-dir' (Join-Path $RepoRoot 'nvt\ground_truth') `
  '--gt0005-precheck' (Join-Path $visibilityDir 'GT_0005_DISPLAY_SUPPRESSION_PRECHECK.json') `
  '--gate-report' (Join-Path $gateDir 'NVT6_OWNERSHIP_GATE_HYPOTHESES.json') `
  '--cluster-report' (Join-Path $clusterDir 'GT_0006_CLUSTER_RIGHT_EDGE_PROBE.json') `
  '--selector-beta' (Join-Path $selectorDir 'GT_0006_SELECTOR_BETA_RESEARCH.json') `
  '--gt0003-canonical' (Join-Path $identityDir 'GT_0003_CANONICAL_CANDIDATE_VIEW_V02.json') `
  '--output' (Join-Path $regressionDir 'NVT6_SOFT_REGRESSION_MATRIX.json')
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 SOFT REGRESSION MATRIX FAILED exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT6 SOFT REGRESSION MATRIX PASS'
Write-Host (Join-Path $regressionDir 'NVT6_SOFT_REGRESSION_MATRIX.json')
Write-Host 'PASS means the research matrix was built. It does NOT mean production promotion is allowed.'
