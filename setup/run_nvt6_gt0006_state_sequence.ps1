$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$gateReport = Join-Path $outputRoot 'nvt6_gate\NVT6_OWNERSHIP_GATE_HYPOTHESES.json'
$evidence = Join-Path $repo 'nvt\cases\GT_0006_VISUAL_STATE_SEQUENCE_EVIDENCE_20260916.json'
$outDir = Join-Path $outputRoot 'nvt6_visual'
$outFile = Join-Path $outDir 'GT_0006_VISUAL_STATE_SEQUENCE.json'

if (-not (Test-Path $gateReport)) {
    throw "Missing gate report: $gateReport"
}
if (-not (Test-Path $evidence)) {
    throw "Missing evidence file: $evidence"
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

python (Join-Path $repo 'tools\nvt\evaluate_gt0006_visual_state_sequence.py') `
    --gate-report $gateReport `
    --evidence $evidence `
    --output $outFile

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT6 GT0006 VISUAL STATE SEQUENCE PASS'
Write-Host "Output: $outFile"
Write-Host 'PASS means research evidence was generated. It does NOT lock production selector/lifecycle rules.'
