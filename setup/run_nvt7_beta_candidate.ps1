$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$outDir = Join-Path $outputRoot 'nvt7_lifecycle'
$graph = Join-Path $outDir 'NVT7_EVENT_STATE_GRAPH.json'
$regression = Join-Path $outDir 'NVT7_SEQUENTIAL_REGRESSION.json'
$outFile = Join-Path $outDir 'NVT7_LIFECYCLE_BETA_CANDIDATE.json'

if (-not (Test-Path $graph)) {
    throw "Missing NVT7 event/state graph: $graph"
}
if (-not (Test-Path $regression)) {
    throw "Missing NVT7 sequential regression: $regression"
}

python (Join-Path $repo 'tools\nvt\build_nvt7_beta_candidate.py') `
    --graph $graph `
    --regression $regression `
    --output $outFile

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT7 LIFECYCLE BETA CANDIDATE PASS'
Write-Host "Output: $outFile"
Write-Host 'PASS means a research beta candidate was generated. It is NOT frozen, held-out validated, or production-ready.'
