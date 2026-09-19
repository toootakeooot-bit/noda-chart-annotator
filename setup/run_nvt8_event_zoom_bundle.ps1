param([double]$SampleSeconds = 5.0)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$common=Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$out=Join-Path $common 'nvt_output\nvt8_validation'
$reg=Join-Path $out 'NVT8_HELD_OUT_SOURCE_REGISTRATION.json'
$lock=Join-Path $out 'NVT8_INSPECTION_LOCK.json'
$windows=Join-Path $repo 'nvt\manifests\NVT8_HELDOUT_COARSE_EVENT_WINDOWS_20260919.json'

python (Join-Path $repo 'tools\nvt\build_nvt8_event_zoom_bundle.py') --registration $reg --inspection-lock $lock --windows $windows --output-dir $out --sample-seconds $SampleSeconds
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host ''
Write-Host 'NVT8 EVENT ZOOM BUNDLE COMPLETE'
Write-Host 'Upload:'
Write-Host '  NVT8_HELDOUT_EVENT_ZOOM_MANIFEST.json'
Write-Host '  NVT8_HELDOUT_EVENT_ZOOM_BUNDLE.pdf'
Write-Host 'Production remains unchanged.'
