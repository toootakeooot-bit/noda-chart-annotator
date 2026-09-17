$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$nvt7Dir = Join-Path $outputRoot 'nvt7_lifecycle'
$nvt71Dir = Join-Path $outputRoot 'nvt7_1_semantic_freeze'
$nvt8Dir = Join-Path $outputRoot 'nvt8_validation'

$partition = Join-Path $repo 'nvt\manifests\NVT8_SOURCE_PARTITION_V1.json'
$beta = Join-Path $nvt7Dir 'NVT7_LIFECYCLE_SCOPED_BETA.json'
$regression = Join-Path $nvt7Dir 'NVT7_FROZEN_SCOPE_REGRESSION.json'
$semanticFreeze = Join-Path $nvt71Dir 'NVT7_1_USDJPY_SEMANTIC_FREEZE_CANDIDATE.json'
$registration = Join-Path $nvt8Dir 'NVT8_HELD_OUT_SOURCE_REGISTRATION.json'
$outFile = Join-Path $nvt8Dir 'NVT8_HELD_OUT_PREFLIGHT.json'

foreach ($p in @($partition, $beta, $regression, $semanticFreeze)) {
    if (-not (Test-Path $p)) {
        throw "Missing required NVT8 preflight input: $p"
    }
}

New-Item -ItemType Directory -Force -Path $nvt8Dir | Out-Null

$pyArgs = @(
    (Join-Path $repo 'tools\nvt\check_nvt8_holdout_preflight.py'),
    '--partition', $partition,
    '--nvt7-scoped-beta', $beta,
    '--nvt7-regression', $regression,
    '--nvt7-semantic-freeze', $semanticFreeze,
    '--output', $outFile
)

if (Test-Path $registration) {
    $pyArgs += @('--held-out-registration', $registration)
    Write-Host "Held-out registration detected: $registration"
} else {
    Write-Host 'No new held-out registration detected yet.'
}

python @pyArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT8 STRICT HELD-OUT PREFLIGHT GENERATED'
Write-Host "Output: $outFile"
Write-Host 'Without a newly registered unseen video, BLOCKED_NO_CLEAN_SOURCE_LEVEL_HOLDOUT is expected and is not an execution failure.'
Write-Host 'After valid pre-inspection registration, READY means teacher-event inspection may begin without tuning frozen rules.'
Write-Host 'NVT8-H historical user adjudication remains supplemental and does not satisfy strict NVT8.'
Write-Host 'Production remains unchanged.'
