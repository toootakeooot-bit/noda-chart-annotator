$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$outDir = Join-Path $outputRoot 'nvt7_lifecycle'
$graph = Join-Path $outDir 'NVT7_EVENT_STATE_GRAPH.json'
$outFile = Join-Path $outDir 'NVT7_SEQUENTIAL_REGRESSION.json'

if (-not (Test-Path $graph)) {
    throw "Missing NVT7 event/state graph: $graph"
}

python (Join-Path $repo 'tools\nvt\run_nvt7_sequential_regression.py') `
    --graph $graph `
    --output $outFile

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT7 SEQUENTIAL REGRESSION PASS'
Write-Host "Output: $outFile"
Write-Host 'PASS means research regression contracts passed. It does NOT freeze lifecycle beta or modify production.'
