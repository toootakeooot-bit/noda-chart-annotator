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

$Exporter = Join-Path $Scripts 'NCA_NormalRun_Exporter.mq4'
$Renderer = Join-Path $Scripts 'NCA_NormalRun_Renderer.mq4'
Copy-Item (Join-Path $RepoRoot 'mt4\NCA_NormalRun_Exporter.mq4') $Exporter -Force
Copy-Item (Join-Path $RepoRoot 'mt4\NCA_NormalRun_Renderer.mq4') $Renderer -Force

$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
New-Item -ItemType Directory -Force -Path (Join-Path $common 'live_input') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $common 'live_output') | Out-Null

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
  & $meta /compile:$Exporter /log
  & $meta /compile:$Renderer /log
  Write-Host 'MetaEditor compile requested.'
} else {
  Write-Host 'MetaEditor path not supplied/found. Compile these scripts in MT4 MetaEditor (F4):'
  Write-Host "  $Exporter"
  Write-Host "  $Renderer"
}

Write-Host 'NCA NORMAL RUN V1 INSTALL PASS'
Write-Host "DataFolder: $DataFolder"
Write-Host "Common: $common"
