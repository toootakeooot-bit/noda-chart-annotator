param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$InputDir = Join-Path $Common 'nvt_input'
$OutDir = Join-Path $Common 'live_output\nvt9_0905_exact_transition'
$OutFile = Join-Path $OutDir 'NVT9_0905_TRANSITION_EXACT_REPLAY.json'

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host 'NVT9 09/05 EXACT TRANSITION REPLAY'
Write-Host '================================'
Write-Host 'Cutoff: 2026-09-05 00:00 exclusive'
Write-Host 'Inputs: NVT H4/H1 closed OHLC'
Write-Host 'Rolling selection: last 600 pre-cutoff bars'
Write-Host 'Warmup/history: pre-cutoff only'
Write-Host 'Production/MT4 writeback: NONE'
Write-Host ''

& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_0905_transition_exact_replay.py') --input-dir $InputDir --symbol $Symbol --cutoff '2026-09-05T00:00:00' --rolling-bars 600 --output $OutFile

$RC = $LASTEXITCODE
if (-not (Test-Path $OutFile)) {
  Write-Host 'No replay artifact was produced.'
  exit $RC
}

$Report = Get-Content -Raw -Encoding UTF8 $OutFile | ConvertFrom-Json
Write-Host ''
Write-Host ('Status: {0}' -f $Report.status)
Write-Host ('Transition exact geometry locked: {0}' -f $Report.transition_exact_geometry_locked)
Write-Host ('Teacher GT exact anchors locked: {0}' -f $Report.teacher_ground_truth_exact_anchors_locked)
Write-Host ('H4: {0} / {1}' -f $Report.timeframes.H4.effective_state,$Report.timeframes.H4.effective_reason_code)
Write-Host ('H4 broken candidate: {0}' -f $Report.timeframes.H4.rolling_transition.broken_candidate.candidate_id)
Write-Host ('H4 break time: {0}' -f $Report.timeframes.H4.rolling_transition.break_time)
Write-Host ('H1: {0} / {1}' -f $Report.timeframes.H1.effective_state,$Report.timeframes.H1.effective_reason_code)
Write-Host ('H1 candidate: {0}' -f $Report.timeframes.H1.effective_candidate.candidate_id)
Write-Host ('Output: {0}' -f $OutFile)

if ($Report.lock.failed_checks.Count -gt 0) {
  Write-Host ''
  Write-Host 'FAILED CHECKS'
  foreach ($x in $Report.lock.failed_checks) {
    Write-Host ('- {0}: {1}' -f $x.name,$x.detail)
  }
}

Write-Host ''
Write-Host 'This artifact locks transition replay only. It does not lock GT_0004 teacher D1 anchors.'
exit $RC
