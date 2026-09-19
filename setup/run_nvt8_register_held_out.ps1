param(
    [Parameter(Mandatory=$true)]
    [string]$VideoPath,
    [string]$RecordingDate = '',
    [switch]$AttestUnseen
)

$ErrorActionPreference = 'Stop'

if (-not $AttestUnseen) {
    throw 'Strict NVT8 registration requires explicit unseen-source attestation, including no inspected related PDF/screenshots/transcript/same-source teacher material.'
}

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$nvt8Dir = Join-Path $common 'nvt_output\nvt8_validation'
$knownCorpus = Join-Path $repo 'nvt\manifests\USDJPY_VIDEO_CORPUS_20260808_20260912.json'
$outFile = Join-Path $nvt8Dir 'NVT8_HELD_OUT_SOURCE_REGISTRATION.json'

if (-not (Test-Path $knownCorpus)) {
    throw "Missing known development corpus: $knownCorpus"
}
if (-not (Test-Path $VideoPath -PathType Leaf)) {
    throw "Video file not found: $VideoPath"
}

New-Item -ItemType Directory -Force -Path $nvt8Dir | Out-Null

$argsList = @(
    (Join-Path $repo 'tools\nvt\register_nvt8_held_out_source.py'),
    '--video', $VideoPath,
    '--known-corpus', $knownCorpus,
    '--output', $outFile,
    '--attest-unseen'
)
if ($RecordingDate) {
    $argsList += @('--recording-date', $RecordingDate)
}

Write-Host 'NVT8 HELD-OUT REGISTRATION'
Write-Host 'This step hashes metadata/file bytes only. It does NOT inspect frames, audio, subtitles, or teacher events.'
Write-Host 'Attestation includes no prior NVT inspection of related PDF/screenshots/transcript/same-source teacher material.'
Write-Host "Video: $VideoPath"
Write-Host ''

python @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT8 HELD-OUT SOURCE REGISTERED BEFORE CONTENT INSPECTION'
Write-Host "Registration: $outFile"
Write-Host 'Do not tune NVT7/NVT7.1 rules after teacher inspection begins.'
Write-Host 'Next: run RUN_NVT8_HELD_OUT_PREFLIGHT.cmd. READY is required before teacher-event review.'
Write-Host 'Production remains unchanged.'
