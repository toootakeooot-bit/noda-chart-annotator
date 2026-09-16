$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'

$batch01 = Join-Path $common 'nvt_output\nvt7_1_post_batch\NVT7_1_POST_BATCH_HANDOFF.json'
$batch02 = Join-Path $common 'nvt_output\nvt7_1_targeted_usdjpy\NVT7_1_USDJPY_TARGETED_REVIEW_BATCH02.json'
$importance = Join-Path $common 'nvt_output\nvt7_1_importance\NVT7_1_B02_03_IMPORTANCE_HANDOFF.json'
$adjudication = Join-Path $repo 'nvt\adjudication\NVT71_USDJPY_USER_ADJUDICATION_BATCH02_20260917.json'
$outputDir = Join-Path $common 'nvt_output\nvt7_1_batch02_final'
$outFile = Join-Path $outputDir 'NVT7_1_BATCH02_FINAL_HANDOFF.json'

foreach ($required in @($batch01, $batch02, $importance, $adjudication)) {
    if (-not (Test-Path $required)) {
        throw "Missing required input: $required"
    }
}

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

python (Join-Path $repo 'tools\nvt\finalize_nvt7_1_usdjpy_batch02.py') `
    --batch01-handoff $batch01 `
    --batch02-targeted $batch02 `
    --batch02-adjudication $adjudication `
    --b02-03-importance $importance `
    --output $outFile

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT7.1 USDJPY BATCH02 FINAL CONTRACT PASS'
Write-Host "Handoff: $outFile"
Write-Host 'Interpretation: B02_03 allows retirement, while B02_04/B02_05 retain the old rising reference. Therefore gentleness/newness/local falling alone are not automatic retirement triggers.'
Write-Host 'Research-only. No Production Normal Run or MT4 object writeback.'
