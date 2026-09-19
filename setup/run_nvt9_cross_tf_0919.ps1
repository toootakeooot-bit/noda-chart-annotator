param([string]$Python='python',[string]$Symbol='USDJPY#')
$ErrorActionPreference='Stop'
$RepoRoot=Split-Path -Parent $PSScriptRoot
$Common=Join-Path $env:APPDATA 'MetaQuotes\\Terminal\\Common\\Files\\noda_draw'
$InputDir=Join-Path $Common 'live_input'
$OutputDir=Join-Path $Common 'live_output'
$Safe=($Symbol -replace '[<>:"/\\\\|?*]','_')
$State=Join-Path $OutputDir ("NORMAL_{0}_live_state.json" -f $Safe)
Write-Host 'NVT9 09/19 CROSS-TF OWNERSHIP REVIEW'
Write-Host '===================================='
Write-Host 'Metrics only. No Production writeback and no automatic owner promotion.'
Write-Host ''
Write-Host '[1/2] Cross-TF self-test'
& $Python (Join-Path $RepoRoot 'tests\\selftest_nvt9_cross_tf.py')
$selfCode=$LASTEXITCODE
if ($selfCode -ne 0) { Write-Host "SELFTEST FAILED - exit=$selfCode"; exit $selfCode }
Write-Host ''
Write-Host '[2/2] Live 09/19 ownership matrix'
if (-not (Test-Path $State)) { Write-Host "FAIL: live state not found: $State"; exit 2 }
& $Python (Join-Path $RepoRoot 'tools\\nvt\\build_cross_tf_review.py') --symbol $Symbol --state $State --input-dir $InputDir --output-dir $OutputDir
$code=$LASTEXITCODE
if ($code -ne 0) { Write-Host "CROSS-TF REVIEW FAILED - exit=$code"; exit $code }
Write-Host ''
Write-Host 'CROSS-TF REVIEW PASS'
Write-Host ("TXT : {0}" -f (Join-Path $OutputDir 'NVT9_USDJPY_CROSS_TF_0919.txt'))
Write-Host ("JSON: {0}" -f (Join-Path $OutputDir 'NVT9_USDJPY_CROSS_TF_0919.json'))
Write-Host ''
Write-Host 'Next: inspect same-family ownership, including anchor-span evidence, before resuming Visibility V4.'
exit 0
