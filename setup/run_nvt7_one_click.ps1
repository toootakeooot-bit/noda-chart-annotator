$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$manifestPath = Join-Path $PSScriptRoot 'NVT7_PIPELINE.json'
if (-not (Test-Path $manifestPath)) {
    throw "Missing pipeline manifest: $manifestPath"
}

$manifest = Get-Content -Raw -Encoding UTF8 $manifestPath | ConvertFrom-Json
$expectedBranch = [string]$manifest.expected_branch
$currentBranch = (& git rev-parse --abbrev-ref HEAD).Trim()
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($currentBranch -ne $expectedBranch) {
    Write-Host ''
    Write-Host 'NVT7 ONE-CLICK STOPPED: wrong repository branch.' -ForegroundColor Yellow
    Write-Host "Expected: $expectedBranch"
    Write-Host "Actual  : $currentBranch"
    Write-Host ''
    Write-Host 'This stop is intentional so NVT0-NVT8 research never changes the Production Normal Run branch.'
    Write-Host 'Recommended operator setup: keep this folder for Production and use a dedicated NVT worktree folder.'
    Write-Host 'After the NVT worktree is created, always run RUN_NVT7_ONE_CLICK.cmd from that NVT folder.'
    exit 21
}

$dirty = @(& git status --porcelain)
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($dirty.Count -gt 0) {
    Write-Host ''
    Write-Host 'NVT7 ONE-CLICK STOPPED: repository has local changes.' -ForegroundColor Yellow
    $dirty | ForEach-Object { Write-Host $_ }
    Write-Host 'Commit/stash/remove the local changes before automatic pull.'
    exit 20
}

Write-Host '=== NVT7 ONE-CLICK: update repository ==='
& git fetch origin
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& git pull --ff-only origin $expectedBranch
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Reload manifest after pull so future stages can be added without changing this entry point.
$manifest = Get-Content -Raw -Encoding UTF8 $manifestPath | ConvertFrom-Json
$head = (& git rev-parse --short HEAD).Trim()
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ''
Write-Host "Branch: $expectedBranch"
Write-Host "HEAD  : $head"
Write-Host ''
Write-Host '=== NVT7 ONE-CLICK: run available stages ==='

$stageResults = @()
foreach ($stage in $manifest.stages) {
    $scriptPath = Join-Path $repo ([string]$stage.script)
    $required = [bool]$stage.required

    if (-not (Test-Path $scriptPath)) {
        if ($required) {
            throw "Required NVT7 stage script missing: $scriptPath"
        }
        $stageResults += [pscustomobject]@{
            id = $stage.id
            name = $stage.name
            status = 'SKIPPED_MISSING_OPTIONAL'
            script = $stage.script
        }
        continue
    }

    Write-Host ''
    Write-Host ("--- {0}: {1} ---" -f $stage.id, $stage.name)
    & powershell -NoProfile -ExecutionPolicy Bypass -File $scriptPath
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        $stageResults += [pscustomobject]@{
            id = $stage.id
            name = $stage.name
            status = 'FAILED'
            exit_code = $code
            script = $stage.script
        }
        throw "NVT7 stage failed: $($stage.id) exit=$code"
    }

    $stageResults += [pscustomobject]@{
        id = $stage.id
        name = $stage.name
        status = 'PASS_GENERATED'
        exit_code = 0
        script = $stage.script
    }
}

$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$outputRoot = Join-Path $common 'nvt_output'
$bundleDir = Join-Path $outputRoot 'nvt7_handoff'
$bundlePath = Join-Path $bundleDir 'NVT7_HANDOFF_BUNDLE.json'
New-Item -ItemType Directory -Force -Path $bundleDir | Out-Null

$artifacts = @()
foreach ($rel in $manifest.bundle_outputs) {
    $path = Join-Path $outputRoot ([string]$rel)
    if (Test-Path $path) {
        $raw = Get-Content -Raw -Encoding UTF8 $path
        $parsed = $raw | ConvertFrom-Json
        $artifacts += [pscustomobject]@{
            relative_path = $rel
            exists = $true
            content = $parsed
        }
    } else {
        $artifacts += [pscustomobject]@{
            relative_path = $rel
            exists = $false
            content = $null
        }
    }
}

$bundle = [pscustomobject]@{
    schema = 'nvt7-handoff-bundle/0.1'
    status = 'RESEARCH_ONLY'
    generated_at_local = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
    branch = $expectedBranch
    head = $head
    stages = $stageResults
    artifacts = $artifacts
    production_writeback = $false
    normal_run_modified = $false
    mt4_object_writeback = $false
}

$bundle | ConvertTo-Json -Depth 100 | Set-Content -Encoding UTF8 $bundlePath

Write-Host ''
Write-Host 'NVT7 ONE-CLICK PASS'
Write-Host "HEAD: $head"
Write-Host "Upload only this file: $bundlePath"
Write-Host 'PASS means all currently-manifested NVT7 research stages generated successfully; it does not freeze lifecycle beta or promote production.'
