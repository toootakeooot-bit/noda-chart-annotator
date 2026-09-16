$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$outDir = Join-Path $outputRoot 'nvt7_lifecycle'
$beta = Join-Path $outDir 'NVT7_LIFECYCLE_BETA_CANDIDATE.json'
$outFile = Join-Path $outDir 'NVT7_LIFECYCLE_SCOPED_BETA.json'

if (-not (Test-Path $beta)) {
    throw "Missing NVT7 lifecycle beta candidate: $beta"
}

python (Join-Path $repo 'tools\nvt\build_nvt7_scoped_freeze.py') `
    --beta-candidate $beta `
    --output $outFile

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT7 SCOPED BETA FREEZE PASS'
Write-Host "Output: $outFile"
Write-Host 'PASS freezes only the evidence-supported research scope. Deferred triggers/transitions remain explicitly out of scope and production is unchanged.'
