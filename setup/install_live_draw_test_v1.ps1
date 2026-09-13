param(
  [string]$TestDataFolder = "$env:APPDATA\MetaQuotes\Terminal\5E04AEF9214FDC3BAD96E2E3E56E4ADA",
  [string]$TerminalRoot = "C:\Program Files (x86)\XMTrading MT4 - コピー (5)"
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Experts = Join-Path $TestDataFolder 'MQL4\Experts'
$Indicators = Join-Path $TestDataFolder 'MQL4\Indicators'

if (!(Test-Path (Join-Path $TestDataFolder 'MQL4'))) {
  throw "TEST DataFolder not found or invalid: $TestDataFolder"
}

New-Item -ItemType Directory -Force -Path $Experts | Out-Null
New-Item -ItemType Directory -Force -Path $Indicators | Out-Null

$Exporter = Join-Path $Experts 'NCA_TEST_MarketExporter.mq4'
$Renderer = Join-Path $Indicators 'NCA_TEST_LiveDraw_Renderer.mq4'
Copy-Item (Join-Path $RepoRoot 'mt4\NCA_TEST_MarketExporter.mq4') $Exporter -Force
Copy-Item (Join-Path $RepoRoot 'mt4\NCA_TEST_LiveDraw_Renderer.mq4') $Renderer -Force

$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
New-Item -ItemType Directory -Force -Path (Join-Path $common 'live_input') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $common 'live_output') | Out-Null

$metaCandidates = @(
  (Join-Path $TerminalRoot 'metaeditor.exe'),
  (Join-Path $TerminalRoot 'metaeditor64.exe')
)
if (Test-Path $TerminalRoot) {
  $metaCandidates += Get-ChildItem -Path $TerminalRoot -Filter 'metaeditor*.exe' -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
}
$meta = $metaCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if ($meta) {
  Write-Host "MetaEditor: $meta"
  & $meta /compile:$Exporter /log
  & $meta /compile:$Renderer /log
  Write-Host 'MetaEditor compile requested.'
} else {
  Write-Host 'MetaEditor not found automatically.'
  Write-Host 'Source files are installed correctly. Open TEST MT4 -> F4 and compile these two files manually:'
  Write-Host "  $Exporter"
  Write-Host "  $Renderer"
}

Write-Host 'NCA LIVE DRAW TEST INSTALL PASS'
Write-Host "DataFolder: $TestDataFolder"
Write-Host "Common: $common"
