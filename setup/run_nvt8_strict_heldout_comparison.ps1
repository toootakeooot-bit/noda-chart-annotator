$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$nvt8 = Join-Path $common 'nvt_output\nvt8_validation'
$nvt7 = Join-Path $common 'nvt_output\nvt7_lifecycle'
$inputDir = Join-Path $common 'nvt_input'

$registry = Join-Path $repo 'nvt\manifests\NVT8_TEACHER_EVENT_REGISTRY_20260919.json'
$replay = Join-Path $nvt8 'NVT8_STRICT_REPLAY_BUNDLE.json'
$preflight = Join-Path $nvt8 'NVT8_HELD_OUT_PREFLIGHT.json'
$nvt7Regression = Join-Path $nvt7 'NVT7_FROZEN_SCOPE_REGRESSION.json'
$out = Join-Path $nvt8 'NVT8_STRICT_HELDOUT_COMPARISON.json'

foreach ($required in @($registry, $replay, $preflight)) {
  if (-not (Test-Path $required)) {
    throw "Missing required input: $required"
  }
}

Write-Host '[1/2] Refresh frozen NVT7 regression (no tuning)...'
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo 'setup\run_nvt7_frozen_scope_regression.ps1')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path $nvt7Regression)) {
  throw "Missing NVT7 frozen regression after refresh: $nvt7Regression"
}

Write-Host '[2/2] Compare frozen NVT against held-out teacher events...'
python (Join-Path $repo 'tools\nvt\compare_nvt8_heldout.py') `
  --registry $registry `
  --replay $replay `
  --nvt7-regression $nvt7Regression `
  --preflight $preflight `
  --input-dir $inputDir `
  --output $out

$err = $LASTEXITCODE
Write-Host ''
if ($err -eq 0) {
  Write-Host 'NVT8 STRICT HELD-OUT COMPARISON PASS'
  Write-Host "Upload: $out"
  Write-Host 'Production remains unchanged. NVT9 review may start only after this report is audited.'
  exit 0
}
if ($err -eq 4) {
  Write-Host 'NVT8 STRICT HELD-OUT COMPARISON FAIL'
  Write-Host "Upload the failure report unchanged: $out"
  Write-Host 'Do NOT tune and rerun this same held-out source.'
  Write-Host 'Production remains unchanged.'
  exit 4
}
Write-Host "NVT8 comparison runner error: exit=$err"
Write-Host "Audit file if created: $out"
exit $err
