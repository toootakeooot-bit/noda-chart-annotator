param(
    [double]$SampleSeconds = 10.0
)

$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$nvt8Dir = Join-Path $common 'nvt_output\nvt8_validation'
$registration = Join-Path $nvt8Dir 'NVT8_HELD_OUT_SOURCE_REGISTRATION.json'

if (-not (Test-Path $registration)) {
    throw "Missing NVT8 held-out registration: $registration"
}

python (Join-Path $repo 'tools\nvt\build_nvt8_heldout_review_bundle.py') `
    --registration $registration `
    --repo $repo `
    --output-dir $nvt8Dir `
    --sample-seconds $SampleSeconds

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT8 HELD-OUT REVIEW BUNDLE GENERATED'
Write-Host "Output folder: $nvt8Dir"
Write-Host 'Upload these three files to ChatGPT:'
Write-Host '  NVT8_INSPECTION_LOCK.json'
Write-Host '  NVT8_HELDOUT_REVIEW_MANIFEST.json'
Write-Host '  NVT8_HELDOUT_REVIEW_BUNDLE.pdf'
Write-Host ''
Write-Host 'Important: the inspection lock is now active. Do not tune NVT7/NVT7.1 rules using this held-out source.'
Write-Host 'Production remains unchanged.'
