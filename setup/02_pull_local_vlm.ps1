$ErrorActionPreference = "Stop"
$model = if ($env:NODA_VLM_MODEL) { $env:NODA_VLM_MODEL } else { "qwen3-vl:8b" }
Write-Host "Pulling local vision model: $model"
ollama pull $model
Write-Host "PASS: model is available locally: $model"
Write-Host "Next: .\setup\03_verify_local_vlm.ps1"
