$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$outDir = Join-Path $outputRoot 'nvt7_lifecycle'
$scoped = Join-Path $outDir 'NVT7_LIFECYCLE_SCOPED_BETA.json'
$regression = Join-Path $outDir 'NVT7_SEQUENTIAL_REGRESSION.json'
$outFile = Join-Path $outDir 'NVT7_FROZEN_SCOPE_REGRESSION.json'

if (-not (Test-Path $scoped)) {
    throw "Missing NVT7 scoped beta: $scoped"
}
if (-not (Test-Path $regression)) {
    throw "Missing NVT7 sequential regression: $regression"
}

python (Join-Path $repo 'tools\nvt\run_nvt7_frozen_scope_regression.py') `
    --scoped-beta $scoped `
    --sequential-regression $regression `
    --output $outFile

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT7 FROZEN SCOPE REGRESSION PASS'
Write-Host "Output: $outFile"
Write-Host 'PASS means the scoped NVT7 beta is internally regression-consistent and ready for NVT8 held-out validation of only that frozen scope. Production remains unchanged.'
