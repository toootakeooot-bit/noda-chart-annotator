$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$nvt7Dir = Join-Path $outputRoot 'nvt7_lifecycle'
$nvt8Dir = Join-Path $outputRoot 'nvt8_validation'

$partition = Join-Path $repo 'nvt\manifests\NVT8_SOURCE_PARTITION_V1.json'
$beta = Join-Path $nvt7Dir 'NVT7_LIFECYCLE_SCOPED_BETA.json'
$regression = Join-Path $nvt7Dir 'NVT7_FROZEN_SCOPE_REGRESSION.json'
$outFile = Join-Path $nvt8Dir 'NVT8_HELD_OUT_PREFLIGHT.json'

foreach ($p in @($partition, $beta, $regression)) {
    if (-not (Test-Path $p)) {
        throw "Missing required NVT8 preflight input: $p"
    }
}

python (Join-Path $repo 'tools\nvt\check_nvt8_holdout_preflight.py') `
    --partition $partition `
    --nvt7-scoped-beta $beta `
    --nvt7-regression $regression `
    --output $outFile

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT8 HELD-OUT PREFLIGHT GENERATED'
Write-Host "Output: $outFile"
Write-Host 'A BLOCKED result is an expected research gate when no clean source-level held-out video is available.'
Write-Host 'Production remains unchanged.'
