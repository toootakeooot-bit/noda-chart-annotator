$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$inputDir = Join-Path $common 'nvt_input'
$priorBundle = Join-Path $common 'nvt_output\nvt8h_usdjpy\NVT8H_USDJPY_REVIEW_BUNDLE.json'
$outputDir = Join-Path $common 'nvt_output\nvt7_1_targeted_usdjpy'
$outFile = Join-Path $outputDir 'NVT7_1_USDJPY_TARGETED_REVIEW_BATCH02.json'

if (-not (Test-Path $inputDir)) {
    throw "Missing NVT input directory: $inputDir"
}
if (-not (Test-Path $priorBundle)) {
    throw "Missing Batch01 historical review bundle: $priorBundle"
}

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

python (Join-Path $repo 'tools\nvt\build_nvt7_1_usdjpy_targeted_review.py') `
    --input-dir $inputDir `
    --prior-bundle $priorBundle `
    --output $outFile `
    --symbol 'USDJPY#' `
    --per-pattern 4

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT7.1 USDJPY TARGETED REVIEW BATCH02 PASS'
Write-Host "Output: $outFile"
Write-Host 'Upload this one JSON file to ChatGPT. ChatGPT will inspect the targeted cases first and ask only for genuinely ambiguous/high-impact judgments.'
Write-Host 'PASS means bundle generation succeeded; it does not validate the NVT7.1 hypotheses.'
