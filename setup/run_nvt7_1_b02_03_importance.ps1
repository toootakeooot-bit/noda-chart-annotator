$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$targeted = Join-Path $common 'nvt_output\nvt7_1_targeted_usdjpy\NVT7_1_USDJPY_TARGETED_REVIEW_BATCH02.json'
$adjudication = Join-Path $repo 'nvt\adjudication\NVT71_B02_03_USER_OPERATIONAL_ADJUDICATION_20260916.json'
$outDir = Join-Path $common 'nvt_output\nvt7_1_importance'
$outFile = Join-Path $outDir 'NVT7_1_B02_03_IMPORTANCE_HANDOFF.json'

if (-not (Test-Path $targeted)) {
    throw "Missing targeted Batch02 bundle: $targeted"
}
if (-not (Test-Path $adjudication)) {
    throw "Missing B02_03 adjudication: $adjudication"
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

python (Join-Path $repo 'tools\nvt\build_nvt7_1_b02_03_importance_handoff.py') `
    --targeted-bundle $targeted `
    --adjudication $adjudication `
    --output $outFile

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT7.1 B02_03 LINE IMPORTANCE PASS'
Write-Host "Output: $outFile"
Write-Host 'PASS means research contracts are represented consistently. It does NOT mean teacher validation or Production readiness.'
