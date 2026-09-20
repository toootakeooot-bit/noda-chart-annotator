param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$OutDir = Join-Path $Common 'live_output'
$Gate = Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_GATE_0919.json'
$Auto = Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_ADJUDICATION_0919_AUTO.json'
$Overrides = Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_OVERRIDES_0919.json'
$Final = Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_ADJUDICATION_0919_FINAL.json'
$V4 = Join-Path $OutDir 'NVT9_USDJPY_V4_VISIBILITY_DECISION_0919.json'
$OwnerEvidence = Join-Path $OutDir 'NVT9_USDJPY_OWNER_EVIDENCE_REVIEW_0919.json'

Write-Host 'NVT9 09/19 PHASE-1 ADVANCE'
Write-Host '=========================='
Write-Host 'This runner advances only research/audit gates. Production and MT4 drawing remain untouched.'
Write-Host ''

Write-Host '[A] Cross-timeframe ownership matrix'
& (Join-Path $PSScriptRoot 'run_nvt9_cross_tf_0919.ps1') -Python $Python -Symbol $Symbol
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ''
Write-Host '[A2] Threshold-free owner evidence review'
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt9_owner_evidence_review.py')
if ($LASTEXITCODE -ne 0) { Write-Host "OWNER EVIDENCE SELFTEST FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }
& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_owner_evidence_review.py') --matrix (Join-Path $OutDir 'NVT9_USDJPY_CROSS_TF_0919.json') --output $OwnerEvidence
if ($LASTEXITCODE -ne 0) { Write-Host "OWNER EVIDENCE REVIEW FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host ''
Write-Host '[B] Conservative ownership adjudication + V3.5 gate'
& (Join-Path $PSScriptRoot 'run_nvt9_ownership_adjudication_0919.ps1') -Python $Python -Symbol $Symbol
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path $Gate)) {
  Write-Host "FAIL: ownership gate output not found: $Gate"
  exit 3
}
$GatePayload = Get-Content -Raw -Encoding UTF8 $Gate | ConvertFrom-Json

$Adjudication = $Auto

Write-Host ''
Write-Host '[C] V4 decision input'
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt9_v4_visibility_decision.py')
if ($LASTEXITCODE -ne 0) { Write-Host "V4 SELFTEST FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_v4_visibility_decision.py') --gate $Gate --adjudication $Adjudication --output $V4
if ($LASTEXITCODE -ne 0) { Write-Host "V4 DECISION BUILD FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host ''
Write-Host '[D] Pre-arm V5 regression tooling'
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt9_visibility_invariants.py')
if ($LASTEXITCODE -ne 0) { Write-Host "V5 SELFTEST FAILED - exit=$LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host ''
Write-Host 'PHASE-1 ADVANCE COMPLETE'
Write-Host ("V3.5 gate: {0}" -f $GatePayload.status)
Write-Host ("V4 report : {0}" -f $V4)
if ($GatePayload.status -ne 'PASS_V3_5') {
  Write-Host ''
  Write-Host 'STOP POINT: V3.5 is blocked by non-exact ownership rows.'
  Write-Host 'Use the generated OWNERSHIP_OVERRIDES_0919_TEMPLATE.json for explicit teacher/manual adjudication.'
} else {
  Write-Host ''
  Write-Host 'V3.5 PASS. V4 is now ready for visual policy selection.'
  Write-Host 'No visibility suppression is auto-applied.'
}
Write-Host ''
Write-Host '[E] Package latest review evidence'
$ReviewZip = Join-Path $env:USERPROFILE 'Downloads\NVT9_0919_REVIEW_LATEST.zip'
$ReviewFiles = @(
  (Join-Path $OutDir 'NVT9_USDJPY_NORMAL_VS_FULL_HISTORY_0919.json'),
  (Join-Path $OutDir 'NVT9_USDJPY_DEEP_LIFECYCLE_STATE_0919.json'),
  (Join-Path $OutDir 'NVT9_USDJPY_DEEP_LIFECYCLE_AUDIT_0919.json'),
  (Join-Path $OutDir 'NVT9_USDJPY_CROSS_TF_0919.json'),
  (Join-Path $OutDir 'NVT9_USDJPY_OWNER_EVIDENCE_REVIEW_0919.json'),
  (Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_ADJUDICATION_0919_AUTO.json'),
  (Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_OVERRIDES_0919_TEMPLATE.json'),
  (Join-Path $OutDir 'NVT9_USDJPY_OWNERSHIP_GATE_0919.json'),
  (Join-Path $OutDir 'NVT9_USDJPY_V4_VISIBILITY_DECISION_0919.json')
) | Where-Object { Test-Path $_ }
if ($ReviewFiles.Count -gt 0) {
  Compress-Archive -Force -Path $ReviewFiles -DestinationPath $ReviewZip
  Write-Host ("Review ZIP: {0}" -f $ReviewZip)
} else {
  Write-Host 'Review ZIP skipped: no evidence files found.'
}
Write-Host ''
Write-Host 'No Production, Renderer, snapshot, or NCA_DRAW__ writeback occurred.'
exit 0
