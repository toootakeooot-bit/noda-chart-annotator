$ErrorActionPreference = "Stop"
Write-Host "NODA Chart Annotator v0.5 - PDF-only local setup"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python was not found in PATH."
}

python -m pip install -r "$PSScriptRoot\..\requirements-local.txt"

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "Ollama not found. Installing with winget..."
    winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
  } else {
    throw "Ollama is not installed and winget is unavailable. Install Ollama, then rerun this script."
  }
}

Write-Host "PASS: local PDF-only dependencies are installed."
Write-Host "Next: .\setup\02_pull_local_vlm.ps1"
