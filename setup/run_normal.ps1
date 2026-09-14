param(
  [string]$Python = 'python',
  [string]$Symbol = ''
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$inputDir = Join-Path $common 'live_input'
$outputDir = Join-Path $common 'live_output'
New-Item -ItemType Directory -Force -Path $inputDir | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$argsList = @(
  (Join-Path $RepoRoot 'tools\run_normal.py'),
  '--input-dir', $inputDir,
  '--output-dir', $outputDir
)
if ($Symbol -ne '') {
  $argsList += @('--symbol', $Symbol)
}

& $Python @argsList
$code = $LASTEXITCODE
if ($code -ne 0) {
  Write-Host "NCA NORMAL RUN FAILED / LAST VALID DRAWING KEPT (exit=$code)"
  exit $code
}

Write-Host 'NCA NORMAL RUN REBUILD + SNAPSHOT PASS'
Write-Host 'Next: render the validated NORMAL_<symbol>_live_snapshot.csv in MT4 with the Normal Run renderer.'
