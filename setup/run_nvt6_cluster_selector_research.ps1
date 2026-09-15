param(
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$gateDir = Join-Path $outputRoot 'nvt6_gate'
$selectorDir = Join-Path $outputRoot 'nvt6_selector'
$clusterDir = Join-Path $outputRoot 'nvt6_cluster'

$gate = Join-Path $gateDir 'NVT6_OWNERSHIP_GATE_HYPOTHESES.json'
$prerank = Join-Path $selectorDir 'GT_0006_SELECTOR_PRERANK.json'

if (!(Test-Path $gate)) {
  Write-Host "NVT6 CLUSTER RESEARCH FAIL: missing $gate"
  Write-Host 'Run setup\RUN_NVT6_GATE_SELECTOR_RESEARCH.cmd first.'
  exit 2
}
if (!(Test-Path $prerank)) {
  Write-Host "NVT6 CLUSTER RESEARCH FAIL: missing $prerank"
  Write-Host 'Run setup\RUN_NVT6_GATE_SELECTOR_RESEARCH.cmd first.'
  exit 2
}

New-Item -ItemType Directory -Force -Path $clusterDir | Out-Null
New-Item -ItemType Directory -Force -Path $selectorDir | Out-Null

Write-Host 'NVT6 CLUSTER / SELECTOR BETA RESEARCH START'
Write-Host 'Research only. Production Normal Run / NCA_DRAW__ / MT4 remain untouched.'
Write-Host ''

$clusterOut = Join-Path $clusterDir 'GT_0006_CLUSTER_RIGHT_EDGE_PROBE.json'
Write-Host '1/2 GT_0006 cluster-right-edge sensitivity probe'
& $Python (Join-Path $RepoRoot 'tools\nvt\probe_gt0006_cluster_right_edge.py') `
  '--gate-report' $gate `
  '--output' $clusterOut
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 CLUSTER RESEARCH STOPPED at cluster probe exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
$betaOut = Join-Path $selectorDir 'GT_0006_SELECTOR_BETA_RESEARCH.json'
Write-Host '2/2 GT_0006 selector beta research synthesis'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_gt0006_selector_beta_research.py') `
  '--selector-prerank' $prerank `
  '--cluster-probe' $clusterOut `
  '--output' $betaOut
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 CLUSTER RESEARCH STOPPED at selector synthesis exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT6 CLUSTER / SELECTOR BETA RESEARCH PASS'
Write-Host ("Cluster probe: {0}" -f $clusterOut)
Write-Host ("Selector beta research: {0}" -f $betaOut)
Write-Host 'PASS means research evidence was generated. No production selector rule is fixed.'
