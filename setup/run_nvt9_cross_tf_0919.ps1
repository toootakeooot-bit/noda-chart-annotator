param([string]$Python='python',[string]$Symbol='USDJPY#')
$ErrorActionPreference='Stop'
$RepoRoot=Split-Path -Parent $PSScriptRoot
$Common=Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$InputDir=Join-Path $Common 'live_input'
$OutputDir=Join-Path $Common 'live_output'
$Safe=($Symbol -replace '[<>:"/\\|?*]','_')
$LiveState=Join-Path $OutputDir ("NORMAL_{0}_live_state.json" -f $Safe)
$ResearchState=Join-Path $OutputDir 'NVT9_USDJPY_FULL_HISTORY_RESEARCH_STATE_0919.json'
$CurrentAudit=Join-Path $OutputDir 'NVT9_USDJPY_NORMAL_VS_FULL_HISTORY_0919.json'

Write-Host 'NVT9 09/19 CROSS-TF OWNERSHIP REVIEW'
Write-Host '===================================='
Write-Host 'Research only. Production state and MT4 drawing are not changed.'
Write-Host ''

Write-Host '[1/3] Cross-TF self-test'
& $Python (Join-Path $RepoRoot 'tests\selftest_nvt9_cross_tf.py')
$selfCode=$LASTEXITCODE
if ($selfCode -ne 0) { Write-Host "SELFTEST FAILED - exit=$selfCode"; exit $selfCode }

Write-Host ''
Write-Host '[2/3] Compare published Normal Run current vs direct full-history selector'
if (-not (Test-Path $LiveState)) { Write-Host "FAIL: live state not found: $LiveState"; exit 2 }
& $Python (Join-Path $RepoRoot 'tools\nvt\audit_nvt9_normal_vs_full_history.py') --symbol $Symbol --state $LiveState --input-dir $InputDir --output-dir $OutputDir
$code=$LASTEXITCODE
if ($code -ne 0) { Write-Host "FULL-HISTORY AUDIT FAILED - exit=$code"; exit $code }

$AuditPayload=Get-Content -Raw -Encoding UTF8 $CurrentAudit | ConvertFrom-Json
Write-Host ("Current/full-history status: {0}" -f $AuditPayload.status)
Write-Host ("Geometry mismatches: {0}" -f $AuditPayload.mismatch_count)
if ($AuditPayload.mismatch_count -gt 0) {
  Write-Host 'IMPORTANT: live current geometry is not used for V3.5 because it differs from direct full-history selection.'
  Write-Host 'The research-only full-history state will be used instead.'
}

Write-Host ''
Write-Host '[3/3] Build cross-TF matrix from research full-history current state'
if (-not (Test-Path $ResearchState)) { Write-Host "FAIL: research state not found: $ResearchState"; exit 3 }
& $Python (Join-Path $RepoRoot 'tools\nvt\build_cross_tf_review.py') --symbol $Symbol --state $ResearchState --input-dir $InputDir --output-dir $OutputDir
$code=$LASTEXITCODE
if ($code -ne 0) { Write-Host "CROSS-TF REVIEW FAILED - exit=$code"; exit $code }

Write-Host ''
Write-Host 'CROSS-TF REVIEW PASS'
Write-Host ("Current audit: {0}" -f $CurrentAudit)
Write-Host ("Research state: {0}" -f $ResearchState)
Write-Host ("JSON:          {0}" -f (Join-Path $OutputDir 'NVT9_USDJPY_CROSS_TF_0919.json'))
Write-Host ''
Write-Host 'No Production state, Renderer, snapshot source, or NCA_DRAW__ writeback occurred.'
exit 0
