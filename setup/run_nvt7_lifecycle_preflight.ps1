$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$gt0006Sequence = Join-Path $outputRoot 'nvt6_visual\GT_0006_VISUAL_STATE_SEQUENCE.json'
$outDir = Join-Path $outputRoot 'nvt7_lifecycle'
$outFile = Join-Path $outDir 'NVT7_LIFECYCLE_PREFLIGHT.json'

$gt0002 = Join-Path $repo 'nvt\ground_truth\GT_0002.json'
$gt0004 = Join-Path $repo 'nvt\ground_truth\GT_0004.json'
$gt0005 = Join-Path $repo 'nvt\ground_truth\GT_0005.json'
$tool = Join-Path $repo 'tools\nvt\build_nvt7_lifecycle_preflight.py'

foreach ($required in @($gt0002, $gt0004, $gt0005, $gt0006Sequence, $tool)) {
    if (-not (Test-Path $required)) {
        throw "Missing required NVT7 input: $required"
    }
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

python $tool `
    --gt0002 $gt0002 `
    --gt0004 $gt0004 `
    --gt0005 $gt0005 `
    --gt0006-sequence $gt0006Sequence `
    --output $outFile

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT7 LIFECYCLE PREFLIGHT PASS'
Write-Host "Output: $outFile"
Write-Host 'PASS means the research lifecycle evidence basis is internally consistent.'
Write-Host 'It does NOT fix production lifecycle rules or modify Normal Run / MT4 objects.'
