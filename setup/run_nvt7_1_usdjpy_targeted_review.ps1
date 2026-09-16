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
$windowAnalogueOutFile = Join-Path $analogueOutputDir 'NVT7_1_USDJPY_B02_03_ANALOGUE_BATCH03B.json'

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
Write-Host 'NVT7.1 B02_03 STRICT ANALOGUE SEARCH PASS'
Write-Host "Strict analogue bundle: $analogueOutFile"
Write-Host 'Strict search PASS may contain zero cases; zero cases means the proxy was too selective, not that the user-semantic rule failed.'

python (Join-Path $repo 'tools\nvt\build_nvt7_1_usdjpy_b02_03_window_search.py') `
    --input-dir $inputDir `
    --batch01 $priorBundle `
    --batch02 $outFile `
    --strict-batch03 $analogueOutFile `
    --output $windowAnalogueOutFile `
    --symbol 'USDJPY#' `
    --lookback-snapshots 5 `
    --max-cases 6

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT7.1 B02_03 BACKWARD-WINDOW SEARCH PASS'
Write-Host "Window analogue bundle: $windowAnalogueOutFile"
Write-Host 'Upload BATCH03B JSON to ChatGPT. The 5-snapshot window is a retrieval heuristic only, not an NVT market-rule threshold.'
