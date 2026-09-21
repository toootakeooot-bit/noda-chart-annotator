param(
  [string]$Python = 'python',
  [string]$Symbol = 'USDJPY#'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$InputDir = Join-Path $Common 'nvt_input'
$LiveOutput = Join-Path $Common 'live_output'
$RefOut = Join-Path $LiveOutput 'nvt9_reference_0919'
$DiagOut = Join-Path $RefOut 'diagnostic'
$Manifest = Join-Path $RepoRoot 'nvt\manifests\NVT9_0919_REFERENCE_LINES_V01.json'
$PreviewAudit = Join-Path $LiveOutput 'nvt9_ab_0912_0919\20260919\OLD\output\NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json'
$Safe = ($Symbol -replace '[<>:"/\\|?*]','_')

Write-Host 'NVT9 09/19 REFERENCE RESTORE + STAGE DIAGNOSTIC'
Write-Host '================================================'
Write-Host 'Audit: ID10IQ200'
Write-Host 'Reference: frozen 8 source-TF line families saved on 2026-09-19'
Write-Host ''

$Required = @('D1','H4','H1','M15') | ForEach-Object {
  Join-Path $InputDir ("NVT_{0}_{1}.csv" -f $Safe,$_)
}
$Missing = @($Required | Where-Object { !(Test-Path $_) })
if ($Missing.Count -gt 0) {
  Write-Host 'STOP: deep NVT inputs are missing.'
  Write-Host 'Run NCA_NVT_HistoryExporter once in MT4 with BarsToExport=6000, then rerun this CMD.'
  $Missing | ForEach-Object { Write-Host ("  missing: {0}" -f $_) }
  exit 2
}

New-Item -ItemType Directory -Force -Path $RefOut | Out-Null
New-Item -ItemType Directory -Force -Path $DiagOut | Out-Null

Write-Host '[1/4] Restore frozen 09/19 eight-line reference and fixed numbering'
& $Python (Join-Path $RepoRoot 'tools\nvt\build_nvt9_0919_reference.py') --manifest $Manifest --output-dir $RefOut
if ($LASTEXITCODE -ne 0) { Write-Host 'REFERENCE BUILD FAILED'; exit $LASTEXITCODE }

Write-Host ''
Write-Host '[2/4] Rebuild current 09/19 OLD replay with selector audit'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'run_nvt9_ab_0912_0919.ps1') -Python $Python -Symbol $Symbol
if ($LASTEXITCODE -ne 0) { Write-Host 'CURRENT 09/19 REPLAY FAILED'; exit $LASTEXITCODE }
if (!(Test-Path $PreviewAudit)) { Write-Host ("STOP: preview audit not found: {0}" -f $PreviewAudit); exit 3 }

Write-Host ''
Write-Host '[3/4] Compare R0919-01..08 through A/B/C/D/E stages'
& $Python (Join-Path $RepoRoot 'tools\nvt\diagnose_nvt9_reference_0919.py') --input-dir $InputDir --reference $Manifest --output-dir $DiagOut --preview-audit $PreviewAudit --symbol $Symbol
if ($LASTEXITCODE -ne 0) { Write-Host 'DIAGNOSTIC FAILED'; exit $LASTEXITCODE }

$DiagPath = Join-Path $DiagOut 'NVT9_0919_REFERENCE_DIAGNOSTIC.json'
$Diag = Get-Content -Raw -Encoding UTF8 $DiagPath | ConvertFrom-Json

Write-Host ''
Write-Host 'FIRST-DIVERGENCE SUMMARY'
Write-Host '------------------------'
foreach ($r in $Diag.results) {
  Write-Host ("{0}  {1,-3} {2,-9} -> {3}" -f $r.reference_id,$r.timeframe,$r.structure_level,$r.first_divergence_stage)
  Write-Host ("    {0}" -f $r.reason)
}

Write-Host ''
Write-Host 'INPUT COVERAGE'
Write-Host '--------------'
foreach ($tf in @('D1','H4','H1','M15')) {
  $c = $Diag.input_coverage.$tf
  if ($null -ne $c) {
    Write-Host ("{0}: bars={1} first={2} last={3}" -f $tf,$c.replay_bar_count,$c.first_replay_bar,$c.last_replay_bar)
  }
}

Write-Host ''
Write-Host '[4/4] Install/compile numbered reference viewer'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'install_nvt9_tfmap_preview_auto.ps1')
if ($LASTEXITCODE -ne 0) { Write-Host 'VIEWER INSTALL FAILED'; exit $LASTEXITCODE }

Write-Host ''
Write-Host 'READY - 09/19 FROZEN REFERENCE RESTORED'
Write-Host '---------------------------------------'
Write-Host 'MT4 script: NCA_NVT9_Reference0919_View'
Write-Host 'Reference IDs: R0919-01 ... R0919-08'
Write-Host ("Reference index: {0}" -f (Join-Path $RefOut 'NVT9_0919_REFERENCE_INDEX.txt'))
Write-Host ("Diagnostic:      {0}" -f (Join-Path $DiagOut 'NVT9_0919_REFERENCE_DIAGNOSTIC.txt'))
Write-Host ''
Write-Host 'Run the viewer once with USDJPY# D1/H4/H1/M15 open.'
Write-Host 'Only NVT9_REF0919__ objects are replaced; manual objects are preserved.'
exit 0
