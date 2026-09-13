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

Copy-Item (Join-Path $RepoRoot 'mt4\NCA_TEST_MarketExporter.mq4') (Join-Path $Experts 'NCA_TEST_MarketExporter.mq4') -Force
Copy-Item (Join-Path $RepoRoot 'mt4\NCA_TEST_LiveDraw_Renderer.mq4') (Join-Path $Indicators 'NCA_TEST_LiveDraw_Renderer.mq4') -Force

$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
New-Item -ItemType Directory -Force -Path (Join-Path $common 'live_input') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $common 'live_output') | Out-Null

$meta = Join-Path $TerminalRoot 'metaeditor.exe'
if (Test-Path $meta) {
  & $meta /compile:"$(Join-Path $Experts 'NCA_TEST_MarketExporter.mq4')" /log
  & $meta /compile:"$(Join-Path $Indicators 'NCA_TEST_LiveDraw_Renderer.mq4')" /log
  Write-Host 'MetaEditor compile requested.'
} else {
  Write-Host 'MetaEditor not found; source files installed, compile manually from MT4.'
}

Write-Host 'NCA LIVE DRAW TEST INSTALL PASS'
Write-Host "DataFolder: $TestDataFolder"
Write-Host "Common: $common"
