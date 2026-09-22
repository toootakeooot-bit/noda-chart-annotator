$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$TerminalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal'

$Sources = @(
  'NCA_NVT_HistoryExporter.mq4',
  'NCA_NVT9_TFMap_Preview_Renderer.mq4',
  'NCA_NVT9_History_View.mq4',
  'NCA_NVT9_AB_View.mq4',
  'NCA_NVT9_Reference0919_View.mq4',
  'NCA_NVT9_Return_Live.mq4'
) | ForEach-Object {
  Join-Path $RepoRoot ("mt4\{0}" -f $_)
}

$MissingSources = @($Sources | Where-Object { !(Test-Path $_) })
if ($MissingSources.Count -gt 0) {
  Write-Host 'AUTO INSTALL STOP: one or more NVT9 sources are missing.'
  $MissingSources | ForEach-Object { Write-Host ("  missing: {0}" -f $_) }
  exit 1
}

$candidates = @()
Get-ChildItem -Path $TerminalRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
  $data = $_.FullName
  $scripts = Join-Path $data 'MQL4\Scripts'
  if (!(Test-Path $scripts)) { return }

  $normal = Join-Path $scripts 'NCA_NormalRun_Renderer.mq4'
  $history = Join-Path $scripts 'NCA_NVT_HistoryExporter.mq4'
  if ((Test-Path $normal) -or (Test-Path $history)) {
    $candidates += $data
  }
}

$candidates = @($candidates | Select-Object -Unique)

if ($candidates.Count -eq 0) {
  Write-Host 'AUTO INSTALL STOP: could not identify the NODA MT4 DataFolder.'
  Write-Host 'No file was copied.'
  exit 2
}
if ($candidates.Count -gt 1) {
  Write-Host 'AUTO INSTALL STOP: more than one NODA-like MT4 DataFolder was found.'
  Write-Host 'No file was copied. Candidates:'
  $candidates | ForEach-Object { Write-Host ("  {0}" -f $_) }
  exit 3
}

$DataFolder = $candidates[0]
$Scripts = Join-Path $DataFolder 'MQL4\Scripts'
$Targets = @()

foreach ($Source in $Sources) {
  $Target = Join-Path $Scripts ([System.IO.Path]::GetFileName($Source))
  Copy-Item $Source $Target -Force
  $Targets += $Target
}

$origin = Join-Path $DataFolder 'origin.txt'
$installRoot = ''
if (Test-Path $origin) {
  $installRoot = (Get-Content -Raw $origin).Trim()
}

$metaCandidates = @()
if ($installRoot -ne '') {
  $metaCandidates += (Join-Path $installRoot 'metaeditor.exe')
  $metaCandidates += (Join-Path $installRoot 'metaeditor64.exe')
}
$meta = $metaCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

Write-Host 'NVT9 TFMAP / HISTORY AUTO INSTALL'
Write-Host '================================='
Write-Host ("DataFolder: {0}" -f $DataFolder)
$Targets | ForEach-Object { Write-Host ("Target:     {0}" -f $_) }

$compileMissing = @()
if ($meta) {
  Write-Host ("MetaEditor: {0}" -f $meta)
  foreach ($Target in $Targets) {
    & $meta /compile:$Target /log
    Start-Sleep -Milliseconds 300
    $ex4 = [System.IO.Path]::ChangeExtension($Target, '.ex4')
    if (Test-Path $ex4) {
      Write-Host ("Compiled:   {0}" -f $ex4)
    } else {
      $compileMissing += $Target
    }
  }
} else {
  Write-Host 'MetaEditor was not auto-detected. MQ4 files were copied successfully.'
  $compileMissing = @($Targets)
}

if ($compileMissing.Count -gt 0) {
  Write-Host ''
  Write-Host 'These scripts may require one manual compile in MetaEditor:'
  $compileMissing | ForEach-Object { Write-Host ("  {0}" -f $_) }
}

Write-Host ''
Write-Host 'AUTO INSTALL COMPLETE'
Write-Host 'Installed scripts:'
Write-Host '  NCA_NVT_HistoryExporter'
Write-Host '  NCA_NVT9_TFMap_Preview_Renderer'
Write-Host '  NCA_NVT9_History_View'
Write-Host '  NCA_NVT9_AB_View'
Write-Host '  NCA_NVT9_Reference0919_View'
Write-Host '  NCA_NVT9_Return_Live'
Write-Host ''
Write-Host 'History_View reads historical cases directly and does NOT overwrite the current live preview.'
Write-Host 'Return_Live moves the four target charts back to the latest bar and re-enables AutoScroll.'
exit 0
