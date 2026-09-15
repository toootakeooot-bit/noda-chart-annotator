param(
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$out = Join-Path $outputRoot 'NVT5_REVIEW_BUNDLE_USDJPY.json'

Write-Host 'NVT5 REVIEW BUNDLE EXPORT START'
& $Python (Join-Path $RepoRoot 'tools\nvt\export_nvt5_review_bundle.py') `
  '--output-root' $outputRoot `
  '--output' $out
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT5 REVIEW BUNDLE FAILED exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT5 REVIEW BUNDLE PASS'
Write-Host "Bundle: $out"
Write-Host 'Upload this single JSON file for anchor/candidate audit.'
