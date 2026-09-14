param(
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputDir = Join-Path $common 'live_output'
$snapshot = Join-Path $outputDir ("NORMAL_{0}_live_snapshot.csv" -f $Symbol)
$backup = Join-Path $outputDir ("NORMAL_{0}_live_snapshot.NR7_1_BACKUP.csv" -f $Symbol)

if (!(Test-Path $snapshot)) {
  throw "Valid snapshot not found: $snapshot"
}
if (Test-Path $backup) {
  throw "Safety stop: backup already exists. Restore/remove it before retrying: $backup"
}

$beforeHash = (Get-FileHash -Algorithm SHA256 -Path $snapshot).Hash
$beforeSize = (Get-Item $snapshot).Length

try {
  Move-Item -Path $snapshot -Destination $backup

  Write-Host ''
  Write-Host 'NR7-1 MT4 RENDERER FAILURE PROBE READY'
  Write-Host 'The valid snapshot is TEMPORARILY hidden. Existing MT4 NCA_DRAW__ objects have NOT been touched.'
  Write-Host ''
  Write-Host 'NOW, in MT4:'
  Write-Host '  1. Select USDJPY# H1 chart.'
  Write-Host '  2. Run NCA_NormalRun_Renderer ONCE.'
  Write-Host '  3. Expected Expert log:'
  Write-Host '     NCA NormalRun Renderer: no validated renderable rows; keeping existing drawing. code=-1'
  Write-Host '  4. Press Ctrl+B and confirm the same 16 NCA_DRAW__ H1 objects still exist.'
  Write-Host '  5. Take a screenshot of the Expert log / object list.'
  Write-Host ''
  [void](Read-Host 'After the MT4 check is complete, press Enter here to RESTORE the valid snapshot')
}
finally {
  if ((Test-Path $backup) -and !(Test-Path $snapshot)) {
    Move-Item -Path $backup -Destination $snapshot
  }
}

if (!(Test-Path $snapshot)) {
  throw "RESTORE FAILED: $snapshot"
}

$afterHash = (Get-FileHash -Algorithm SHA256 -Path $snapshot).Hash
$afterSize = (Get-Item $snapshot).Length
if ($beforeHash -ne $afterHash -or $beforeSize -ne $afterSize) {
  throw 'RESTORE HASH CHECK FAILED: restored snapshot is not byte-identical.'
}

Write-Host ''
Write-Host 'NR7-1 SNAPSHOT RESTORE PASS'
Write-Host "SHA256: $afterHash"
Write-Host 'Send the MT4 screenshot showing the failure-safe log and retained NCA_DRAW__ objects for final audit closure.'
