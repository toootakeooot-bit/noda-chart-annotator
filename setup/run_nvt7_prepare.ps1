$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$outDir = Join-Path $outputRoot 'nvt7_lifecycle'
$preflight = Join-Path $outDir 'NVT7_LIFECYCLE_PREFLIGHT.json'
$graph = Join-Path $outDir 'NVT7_EVENT_STATE_GRAPH.json'

& (Join-Path $PSScriptRoot 'run_nvt7_lifecycle_preflight.ps1')
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python (Join-Path $repo 'tools\nvt\build_nvt7_event_state_graph.py') `
    --preflight $preflight `
    --output $graph

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT7 PREPARE PASS'
Write-Host "Preflight: $preflight"
Write-Host "Event/state graph: $graph"
Write-Host 'PASS means NVT7 research artifacts were generated. Lifecycle beta is NOT frozen and production is unchanged.'
