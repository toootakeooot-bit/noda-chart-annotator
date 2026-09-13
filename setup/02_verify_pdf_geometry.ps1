$ErrorActionPreference = "Stop"
python "$PSScriptRoot\..\tools\pdf_geometry_extractor_compat.py" --self-test
if ($LASTEXITCODE -ne 0) { throw "PDF geometry self-test failed with exit code $LASTEXITCODE" }
Write-Host "PASS: deterministic PDF geometry engine verified with OpenCV compatibility shim."
