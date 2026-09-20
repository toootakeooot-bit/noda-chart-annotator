param(
  [Parameter(Mandatory=$true)]
  [ValidateSet('20260822','20260829','20260905','20260912')]
  [string]$Case
)

$ErrorActionPreference = 'Stop'
$Common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\noda_draw'
$LiveOut = Join-Path $Common 'live_output'
$CaseOut = Join-Path (Join-Path $LiveOut 'nvt9_history_4w_0919') (Join-Path $Case 'output')
$SrcPreview = Join-Path $CaseOut 'NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv'
$SrcAudit = Join-Path $CaseOut 'NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json'
$DstPreview = Join-Path $LiveOut 'NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv'
$DstAudit = Join-Path $LiveOut 'NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json'

if (!(Test-Path $SrcPreview)) { throw "Historical preview not found: $SrcPreview" }
if (!(Test-Path $SrcAudit)) { throw "Historical audit not found: $SrcAudit" }

Copy-Item -Force $SrcPreview $DstPreview
Copy-Item -Force $SrcAudit $DstAudit
Write-Host ("ACTIVATED NVT9 HISTORY CASE: {0}" -f $Case)
Write-Host 'Run NCA_NVT9_TFMap_Preview_Renderer on the MT4 charts to view this historical case.'
