$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw\nvt_output'
$input = Join-Path $common 'GT_0006_TURN_RECALL_DIAGNOSTIC.json'
$output = Join-Path $common 'GT_0006_MICRO_DOW_PROTOTYPE.json'
$tool = Join-Path $repo 'tools\nvt\prototype_micro_dow.py'

Write-Host 'NVT5 GT_0006 MICRO-DOW PROTOTYPE START'
Write-Host 'Research only. Production Normal Run / NCA_DRAW__ are not modified.'

if (-not (Test-Path $input)) {
    throw "Diagnostic input not found: $input"
}
if (-not (Test-Path $tool)) {
    throw "Prototype tool not found: $tool"
}

python $tool --diagnostic $input --output $output
if ($LASTEXITCODE -ne 0) {
    throw "Micro-Dow prototype failed exit=$LASTEXITCODE"
}

Write-Host ''
Write-Host 'NVT5 GT_0006 MICRO-DOW PROTOTYPE PASS'
Write-Host "Output: $output"
Write-Host 'Interpretation: candidate recall only; this does NOT select or render a teacher line.'
