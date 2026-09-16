$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'

$scoped = Join-Path $outputRoot 'nvt7_lifecycle\NVT7_LIFECYCLE_SCOPED_BETA.json'
$historical = Join-Path $outputRoot 'nvt8h_usdjpy\NVT8H_USDJPY_REVIEW_BUNDLE.json'
$adjudication = Join-Path $repo 'nvt\adjudication\NVT8H_USDJPY_USER_ADJUDICATION_BATCH01.json'
$outDir = Join-Path $outputRoot 'nvt7_1_post_batch'
$candidate = Join-Path $outDir 'NVT7_1_POST_BATCH_CANDIDATE.json'
$regression = Join-Path $outDir 'NVT7_1_HISTORICAL_REGRESSION.json'
$handoff = Join-Path $outDir 'NVT7_1_POST_BATCH_HANDOFF.json'

foreach ($required in @($scoped, $historical, $adjudication)) {
    if (-not (Test-Path $required)) {
        throw "Missing required NVT7.1 input: $required"
    }
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Host '[1/3] Build research-only NVT7.1 post-batch candidate...'
python (Join-Path $repo 'tools\nvt\build_nvt7_1_post_batch_candidate.py') `
    --scoped-beta $scoped `
    --adjudication $adjudication `
    --historical-bundle $historical `
    --output $candidate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ''
Write-Host '[2/3] Run USDJPY post-batch contract regression...'
python (Join-Path $repo 'tools\nvt\run_nvt7_1_post_batch_regression.py') `
    --candidate $candidate `
    --output $regression
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ''
Write-Host '[3/3] Build one-file handoff bundle...'
$candidateObj = Get-Content -Raw -Encoding UTF8 $candidate | ConvertFrom-Json
$regressionObj = Get-Content -Raw -Encoding UTF8 $regression | ConvertFrom-Json

$bundle = [ordered]@{
    schema = 'nvt7.1-usdjpy-post-batch-handoff/0.1'
    status = if ($regressionObj.all_contracts_pass -eq $true) { 'PASS_CONTRACTS' } else { 'FAIL_CONTRACTS' }
    symbol_scope = 'USDJPY_ONLY'
    evidence_class = 'USER_OPERATIONAL_EVIDENCE'
    original_nvt7_scoped_beta_unchanged = $true
    candidate = $candidateObj
    regression = $regressionObj
    production_writeback = $false
    normal_run_modified = $false
    mt4_object_writeback = $false
}
$bundle | ConvertTo-Json -Depth 100 | Set-Content -Encoding UTF8 $handoff

Write-Host ''
Write-Host 'NVT7.1 USDJPY POST-BATCH COMPLETE'
Write-Host "Candidate : $candidate"
Write-Host "Regression: $regression"
Write-Host "Upload only: $handoff"
Write-Host 'PASS_CONTRACTS is research contract reproduction only; it is not strict teacher held-out or production validation.'
