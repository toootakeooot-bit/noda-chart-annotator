param(
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'

Write-Host 'NVT6 PREFLIGHT ALL START'
Write-Host '1/2 Structure ownership evidence: GT_0005 / GT_0006 / GT_0007'
& (Join-Path $PSScriptRoot 'run_nvt6_structure_ownership_preflight.ps1') -Python $Python
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 PREFLIGHT STOPPED at ownership step exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host '2/2 Candidate identity audit: GT_0003 / H4'
& (Join-Path $PSScriptRoot 'run_nvt6_gt0003_candidate_identity_audit.ps1') -Python $Python
if ($LASTEXITCODE -ne 0) {
  Write-Host "NVT6 PREFLIGHT STOPPED at identity step exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'NVT6 PREFLIGHT ALL PASS'
Write-Host 'This is research evidence only. Structure Selector beta is not yet promoted or enabled.'
Write-Host 'Production Normal Run / NCA_DRAW__ remain unchanged.'
