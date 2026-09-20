$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$TerminalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal'
$Source = Join-Path $RepoRoot 'mt4\NCA_NVT9_TFMap_Preview_Renderer.mq4'

if (!(Test-Path $Source)) {
  throw "Renderer source not found: $Source"
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
$Target = Join-Path $Scripts 'NCA_NVT9_TFMap_Preview_Renderer.mq4'
Copy-Item $Source $Target -Force

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

Write-Host 'NVT9 TFMAP AUTO INSTALL'
Write-Host '======================='
Write-Host ("DataFolder: {0}" -f $DataFolder)
Write-Host ("Source:     {0}" -f $Source)
Write-Host ("Target:     {0}" -f $Target)

if ($meta) {
  Write-Host ("MetaEditor: {0}" -f $meta)
  & $meta /compile:$Target /log
  Start-Sleep -Milliseconds 500
  $ex4 = [System.IO.Path]::ChangeExtension($Target, '.ex4')
  if (Test-Path $ex4) {
    Write-Host ("Compiled:   {0}" -f $ex4)
  } else {
    Write-Host 'Compile was requested. If the script does not appear in MT4, open MetaEditor and compile the MQ4 once.'
  }
} else {
  Write-Host 'MetaEditor was not auto-detected. The MQ4 was copied successfully.'
  Write-Host 'Open MT4 MetaEditor and compile NCA_NVT9_TFMap_Preview_Renderer.mq4 once.'
}

Write-Host ''
Write-Host 'AUTO INSTALL COMPLETE'
Write-Host 'This installs only the isolated NVT9_TFMAP__ research renderer.'
Write-Host 'Production NCA_DRAW__ objects are not changed.'
exit 0
