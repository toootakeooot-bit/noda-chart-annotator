param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ManifestPath = Join-Path $RepoRoot 'nvt\manifests\NVT9_PROMOTION_SCOPE_V01.json'
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$InputDir = Join-Path $Common 'live_input'
$OutputDir = Join-Path $Common 'live_output'

function Safe-FileSymbol([string]$Value) {
  return ($Value -replace '[<>:"/\\|?*]', '_')
}

Write-Host 'NVT9 USDJPY MT4 SMOKE - BASELINE ONLY'
Write-Host '====================================='

if (!(Test-Path $ManifestPath)) {
  Write-Host "FAIL: NVT9 scope manifest not found: $ManifestPath"
  exit 10
}

$scope = Get-Content -Raw -Path $ManifestPath | ConvertFrom-Json
$badLayer = $false
foreach ($layerName in @('A','B','C','D','E')) {
  $layer = $scope.layers.$layerName
  if ($null -eq $layer -or $layer.decision -ne 'KEEP BASELINE' -or $layer.implementation_target -ne $false) {
    Write-Host "FAIL: NVT9 layer $layerName is not KEEP BASELINE / implementation_target=false"
    $badLayer = $true
  }
}
if ($badLayer -or
    @($scope.implementation_target_layers).Count -ne 0 -or
    $scope.production_semantic_patch -ne $false -or
    $scope.renderer_patch -ne $false -or
    $scope.nca_draw_change -ne $false -or
    $scope.mt4_object_writeback -ne $false) {
  Write-Host 'FAIL: NVT9 no-change scope guard did not pass. Do not run MT4 smoke verification.'
  exit 11
}
Write-Host 'STEP 0 PASS: NVT9 scope = KEEP BASELINE A-E / no Production patch.'

New-Item -ItemType Directory -Force -Path $InputDir | Out-Null
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$safe = Safe-FileSymbol $Symbol
$statusPath = Join-Path $InputDir ("NORMAL_{0}_export_status.csv" -f $safe)
$required = @('D1','H4','H1','M15') | ForEach-Object {
  Join-Path $InputDir ("NORMAL_{0}_{1}.csv" -f $safe, $_)
}
$missing = @($required | Where-Object { !(Test-Path $_) })
if (!(Test-Path $statusPath)) {
  $missing += $statusPath
}

if ($missing.Count -gt 0) {
  Write-Host ''
  Write-Host 'WAITING FOR MT4 EXPORT'
  Write-Host "1) Open $Symbol in MT4."
  Write-Host '2) Run NCA_NormalRun_Exporter once.'
  Write-Host '3) Run this CMD again.'
  Write-Host 'Missing:'
  $missing | ForEach-Object { Write-Host "  $_" }
  exit 2
}

try {
  $exportStatus = Import-Csv -Path $statusPath | Select-Object -First 1
  if ($exportStatus.symbol -ne $Symbol) {
    Write-Host "FAIL: export symbol mismatch. expected=$Symbol actual=$($exportStatus.symbol)"
    exit 12
  }
  Write-Host ("STEP 1 PASS: MT4 export found. exported_at={0} D1={1} H4={2} H1={3} M15={4}" -f
    $exportStatus.exported_at,$exportStatus.D1,$exportStatus.H4,$exportStatus.H1,$exportStatus.M15)
} catch {
  Write-Host "FAIL: could not parse export status: $statusPath"
  throw
}

Write-Host ''
Write-Host 'STEP 2: run existing NR7-1 baseline regression + safe snapshot checks.'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'run_nr7_1_usdjpy.ps1') -Python $Python -Symbol $Symbol
$nrCode = $LASTEXITCODE
if ($nrCode -ne 0) {
  Write-Host "FAIL: NR7-1 did not pass. exit=$nrCode"
  exit $nrCode
}

$snapshot = Join-Path $OutputDir ("NORMAL_{0}_live_snapshot.csv" -f $safe)
$runAudit = Join-Path $OutputDir ("NORMAL_{0}_run_audit.json" -f $safe)
$regression = Join-Path $OutputDir ("NR7_1_{0}_regression.json" -f $Symbol)
if (!(Test-Path $snapshot) -or !(Test-Path $runAudit) -or !(Test-Path $regression)) {
  Write-Host 'FAIL: required Normal Run outputs are missing after NR7-1 PASS.'
  Write-Host "Snapshot:   $snapshot"
  Write-Host "Run audit:  $runAudit"
  Write-Host "Regression: $regression"
  exit 13
}

$normalAudit = Get-Content -Raw -Path $runAudit | ConvertFrom-Json
if ($normalAudit.status -ne 'PASS' -or $normalAudit.snapshot_published -ne $true) {
  Write-Host 'FAIL: Normal Run audit is not PASS / snapshot_published=true.'
  exit 14
}

$reg = Get-Content -Raw -Path $regression | ConvertFrom-Json
$snapshotRows = @(Import-Csv -Path $snapshot)
$expected = [ordered]@{}
foreach ($tf in @('D1','H4','H1','M15')) {
  $value = @($snapshotRows | Where-Object {
    $_.symbol -eq $Symbol -and $_.timeframe -eq $tf
  }).Count
  $expected[$tf] = $value
}

$readyPath = Join-Path $OutputDir ("NVT9_{0}_MT4_SMOKE_READY.json" -f $safe)
$ready = [ordered]@{
  schema = 'nvt9-mt4-smoke-ready/1.0'
  status = 'READY_FOR_MT4_RENDER_VERIFICATION'
  audit_id = 'ID10IQ200'
  symbol = $Symbol
  nvt9_scope_status = $scope.status
  production_patch_applied = $false
  nr7_1_pass = $true
  normal_run_status = $normalAudit.status
  snapshot_published = $normalAudit.snapshot_published
  snapshot = $snapshot
  expected_renderer_rows = $expected
  renderer = 'NCA_NormalRun_Renderer'
  renderer_prefix = 'NCA_DRAW__'
  manual_objects_must_remain_untouched = $true
  remaining_host_action = 'Run unchanged NCA_NormalRun_Renderer once on USDJPY# D1/H4/H1/M15 and visually verify the expected rows/lines.'
}
$ready | ConvertTo-Json -Depth 6 | Set-Content -Path $readyPath -Encoding UTF8

Write-Host ''
Write-Host 'AUTOMATED SIDE PASS - READY FOR ACTUAL MT4 DRAW'
Write-Host "Ready audit: $readyPath"
Write-Host "Snapshot:    $snapshot"
Write-Host ''
Write-Host 'Expected NCA_DRAW__ objects after renderer:'
foreach ($tf in @('D1','H4','H1','M15')) {
  Write-Host ("  {0}: {1}" -f $tf,$expected[$tf])
}
Write-Host ''
Write-Host 'FINAL HOST CHECK:'
Write-Host "  1) Keep $Symbol open in MT4."
Write-Host '  2) D1 -> run NCA_NormalRun_Renderer once.'
Write-Host '  3) H4 -> run NCA_NormalRun_Renderer once.'
Write-Host '  4) H1 -> run NCA_NormalRun_Renderer once.'
Write-Host '  5) M15 -> run NCA_NormalRun_Renderer once.'
Write-Host '  6) Take screenshots of the four charts.'
Write-Host ''
Write-Host 'Do not alter NCA_DRAW__ manually. Non-NCA/manual chart objects must remain untouched.'
exit 0
