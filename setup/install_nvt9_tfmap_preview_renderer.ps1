param(
  [Parameter(Mandatory=$true)]
  [string]$DataFolder,
  [string]$TerminalRoot = ''
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Scripts = Join-Path $DataFolder 'MQL4\Scripts'

if (!(Test-Path (Join-Path $DataFolder 'MQL4'))) {
  throw "MT4 DataFolder not found or invalid: $DataFolder"
}

New-Item -ItemType Directory -Force -Path $Scripts | Out-Null
$Target = Join-Path $Scripts 'NCA_NVT9_TFMap_Preview_Renderer.mq4'
Copy-Item (Join-Path $RepoRoot 'mt4\NCA_NVT9_TFMap_Preview_Renderer.mq4') $Target -Force

$metaCandidates = @()
if ($TerminalRoot -ne '') {
  $metaCandidates += (Join-Path $TerminalRoot 'metaeditor.exe')
  $metaCandidates += (Join-Path $TerminalRoot 'metaeditor64.exe')
  if (Test-Path $TerminalRoot) {
    $metaCandidates += Get-ChildItem -Path $TerminalRoot -Filter 'metaeditor*.exe' -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
  }
}
$meta = $metaCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if ($meta) {
  Write-Host "MetaEditor: $meta"
  & $meta /compile:$Target /log
  Write-Host 'MetaEditor compile requested.'
} else {
  Write-Host 'MetaEditor path not supplied/found. Compile this script in MT4 MetaEditor (F4):'
  Write-Host "  $Target"
}

Write-Host 'NVT9 TFMAP PREVIEW RENDERER INSTALL PASS'
Write-Host "Target: $Target"
Write-Host 'Owned prefix: NVT9_TFMAP__'
Write-Host 'Production NCA_DRAW__ and manual objects are untouched.'
