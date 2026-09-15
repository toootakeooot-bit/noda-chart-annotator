param(
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$gate = Join-Path $outputRoot 'nvt6_gate\NVT6_OWNERSHIP_GATE_HYPOTHESES.json'
$outDir = Join-Path $outputRoot 'nvt6_visual'
$out = Join-Path $outDir 'GT_0006_VISUAL_FINALISTS.json'

if (!(Test-Path $gate)) {
  Write-Host "NVT6 GT0006 VISUAL FINALISTS FAIL: missing $gate"
  Write-Host 'Run setup\RUN_NVT6_GATE_SELECTOR_RESEARCH.cmd first.'
  exit 2
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Host 'NVT6 GT0006 VISUAL FINALISTS START'
Write-Host 'Research only. This does not lock Ground Truth or modify Production/MT4.'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_gt0006_visual_finalists.py') `
  '--gate-report' $gate `
  '--output' $out
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 GT0006 VISUAL FINALISTS FAIL exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT6 GT0006 VISUAL FINALISTS PASS'
Write-Host ("Output: {0}" -f $out)
Write-Host 'PASS means candidate geometry was narrowed by direct video evidence; exact Teacher anchor remains unlocked.'
