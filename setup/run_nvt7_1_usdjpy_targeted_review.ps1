$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$inputDir = Join-Path $common 'nvt_input'
$priorBundle = Join-Path $common 'nvt_output\nvt8h_usdjpy\NVT8H_USDJPY_REVIEW_BUNDLE.json'
$outputDir = Join-Path $common 'nvt_output\nvt7_1_targeted_usdjpy'
$outFile = Join-Path $outputDir 'NVT7_1_USDJPY_TARGETED_REVIEW_BATCH02.json'

$importanceAdjudication = Join-Path $repo 'nvt\adjudication\NVT71_B02_03_USER_OPERATIONAL_ADJUDICATION_20260916.json'
$importanceOutputDir = Join-Path $common 'nvt_output\nvt7_1_importance'
$importanceOutFile = Join-Path $importanceOutputDir 'NVT7_1_B02_03_IMPORTANCE_HANDOFF.json'

$analogueOutputDir = Join-Path $common 'nvt_output\nvt7_1_b02_03_analogues'
$analogueOutFile = Join-Path $analogueOutputDir 'NVT7_1_USDJPY_B02_03_ANALOGUE_BATCH03.json'

if (-not (Test-Path $inputDir)) {
    throw "Missing NVT input directory: $inputDir"
}
if (-not (Test-Path $priorBundle)) {
    throw "Missing Batch01 historical review bundle: $priorBundle"
}
if (-not (Test-Path $importanceAdjudication)) {
    throw "Missing B02_03 user adjudication: $importanceAdjudication"
}

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
New-Item -ItemType Directory -Force -Path $importanceOutputDir | Out-Null
New-Item -ItemType Directory -Force -Path $analogueOutputDir | Out-Null

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
Write-Host "Batch02: $outFile"
Write-Host 'Bundle generation PASS does not validate the hypotheses.'

# B02_03 now has explicit user operational adjudication. Build its research-only
# line-importance/confirmation contract immediately after Batch02 generation so the
# user does not need a second manual command.
python (Join-Path $repo 'tools\nvt\build_nvt7_1_b02_03_importance_handoff.py') `
    --targeted-bundle $outFile `
    --adjudication $importanceAdjudication `
    --output $importanceOutFile

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT7.1 B02_03 LINE IMPORTANCE CONTRACT PASS'
Write-Host "Importance handoff: $importanceOutFile"
Write-Host 'PASS means the research contract is internally consistent; it does NOT mean teacher validation or Production readiness.'

# Search additional future-hidden USDJPY H1 mechanical analogue candidates. This is
# deliberately a proxy search only: it does not claim to objectively detect the
# user-defined structural-high breakout or second-low reaction.
python (Join-Path $repo 'tools\nvt\build_nvt7_1_usdjpy_b02_03_analogue_search.py') `
    --input-dir $inputDir `
    --batch01 $priorBundle `
    --batch02 $outFile `
    --output $analogueOutFile `
    --symbol 'USDJPY#' `
    --max-cases 6

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT7.1 B02_03 ANALOGUE SEARCH PASS'
Write-Host "Analogue bundle: $analogueOutFile"
Write-Host 'Upload the analogue bundle JSON to ChatGPT. Candidate search PASS is not semantic validation.'
