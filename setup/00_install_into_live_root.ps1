param(
  [string]$Target = "$env:USERPROFILE\Downloads\noda_draw_phase6e_daily_collect_v01\noda_draw_phase6e_daily_collect_v01"
)
$ErrorActionPreference = "Stop"
$SourceRoot = (Resolve-Path "$PSScriptRoot\..").Path
if (-not (Test-Path $Target)) { throw "Live root not found: $Target" }
New-Item -ItemType Directory -Force -Path "$Target\tools" | Out-Null
New-Item -ItemType Directory -Force -Path "$Target\spec" | Out-Null
New-Item -ItemType Directory -Force -Path "$Target\setup" | Out-Null
Copy-Item "$SourceRoot\tools\pdf_geometry_extractor.py" "$Target\tools\pdf_geometry_extractor.py" -Force
Copy-Item "$SourceRoot\tools\run_pdf_only_once.py" "$Target\tools\run_pdf_only_once.py" -Force
Copy-Item "$SourceRoot\spec\PDF_GEOMETRY_POLICY.md" "$Target\spec\PDF_GEOMETRY_POLICY.md" -Force
Copy-Item "$SourceRoot\spec\noda_rules_current.json" "$Target\spec\noda_rules_current.json" -Force
Copy-Item "$SourceRoot\requirements-local.txt" "$Target\requirements-local.txt" -Force
Copy-Item "$SourceRoot\run_pdf_only_once.cmd" "$Target\run_pdf_only_once.cmd" -Force
Copy-Item "$SourceRoot\setup\01_install_pdf_geometry.ps1" "$Target\setup\01_install_pdf_geometry.ps1" -Force
Copy-Item "$SourceRoot\setup\02_verify_pdf_geometry.ps1" "$Target\setup\02_verify_pdf_geometry.ps1" -Force
Copy-Item "$SourceRoot\PHASE6J_AUDIT.md" "$Target\PHASE6J_AUDIT.md" -Force
Write-Host "PASS: Phase 6-J v0.6 PDF geometry patch installed into: $Target"
Write-Host "Ollama / OpenAI API / video are NOT used by v0.6."
Write-Host "Next: cd `"$Target`""
Write-Host "Then: .\setup\01_install_pdf_geometry.ps1"
