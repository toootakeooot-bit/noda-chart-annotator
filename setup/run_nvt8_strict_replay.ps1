param(
  [string]$BrokerSymbol = 'USDJPY#',
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$inputDir = Join-Path $common 'nvt_input'
$nvt8Dir = Join-Path $common 'nvt_output\nvt8_validation'
$registry = Join-Path $RepoRoot 'nvt\manifests\NVT8_TEACHER_EVENT_REGISTRY_20260919.json'
$lock = Join-Path $nvt8Dir 'NVT8_INSPECTION_LOCK.json'
$out = Join-Path $nvt8Dir 'NVT8_STRICT_REPLAY_BUNDLE.json'

if (!(Test-Path $lock)) {
  Write-Host "NVT8 FAIL: missing inspection lock: $lock"
  exit 2
}
if (!(Test-Path $registry)) {
  Write-Host "NVT8 FAIL: missing frozen teacher event registry: $registry"
  exit 2
}

Write-Host 'NVT8 STRICT TIME-FROZEN REPLAY'
Write-Host 'Prerequisite: run NCA_NVT_HistoryExporter on USDJPY# in MT4 AFTER the 2026-09-18 market close.'
Write-Host ''

& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt8_strict_replay_bundle.py') `
  '--registry' $registry `
  '--inspection-lock' $lock `
  '--repo' $RepoRoot `
  '--input-dir' $inputDir `
  '--output' $out `
  '--broker-symbol' $BrokerSymbol

$err = $LASTEXITCODE
Write-Host ''
if ($err -eq 0) {
  Write-Host 'NVT8 STRICT REPLAY BUNDLE READY'
  Write-Host "Upload: $out"
  Write-Host 'Production remains unchanged.'
  exit 0
}
if ($err -eq 3) {
  Write-Host 'NVT8 WAITING FOR FRESH MT4 HISTORY EXPORT'
  Write-Host 'Open USDJPY# in MT4 and run NCA_NVT_HistoryExporter once, then rerun this command.'
  Write-Host "Partial audit file: $out"
  exit 3
}
Write-Host "NVT8 STRICT REPLAY FAILED/BLOCKED exit=$err"
Write-Host "Audit file if created: $out"
exit $err
