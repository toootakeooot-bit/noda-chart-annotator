$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$inputDir = Join-Path $common 'nvt_input'
$outputDir = Join-Path $common 'nvt_output\nvt8h_usdjpy'
$outFile = Join-Path $outputDir 'NVT8H_USDJPY_REVIEW_BUNDLE.json'

if (-not (Test-Path $inputDir)) {
    throw "Missing NVT input directory: $inputDir"
}

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

python (Join-Path $repo 'tools\nvt\build_usdjpy_historical_review_bundle.py') `
    --input-dir $inputDir `
    --output $outFile `
    --case-count 8 `
    --symbol 'USDJPY#'

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT8-H USDJPY HISTORICAL REVIEW BUNDLE PASS'
Write-Host "Output: $outFile"
Write-Host 'Upload this one JSON file to ChatGPT. ChatGPT reviews first and asks the user only for judgments it cannot resolve confidently.'
Write-Host 'This is supplemental human-adjudicated historical validation, not strict teacher held-out NVT8.'
