$ErrorActionPreference = 'Stop'

$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$nvt8 = Join-Path $common 'nvt_output\nvt8_validation'
$original = Join-Path $nvt8 'NVT8_STRICT_HELDOUT_COMPARISON.json'
$out = Join-Path $nvt8 'NVT8_STRICT_HELDOUT_COMPARISON_CORRECTED.json'
$repo = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path $original)) {
    throw "Missing original strict NVT8 report: $original"
}

python (Join-Path $repo 'tools\nvt\correct_nvt8_te02_harness_bug.py') `
  --original-report $original `
  --output $out

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT8 HARNESS CORRECTION COMPLETE'
Write-Host 'Original FAIL report is preserved unchanged.'
Write-Host 'No frozen NVT rule, teacher registry, market data, or Production code was changed.'
Write-Host "Upload: $out"
