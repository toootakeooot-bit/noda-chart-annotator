$ErrorActionPreference = "Stop"
$model = if ($env:NODA_VLM_MODEL) { $env:NODA_VLM_MODEL } else { "qwen3-vl:8b" }
try {
  $body = @{
    model = $model
    stream = $false
    format = "json"
    messages = @(@{ role = "user"; content = 'Return exactly {"status":"PASS"} as JSON.' })
  } | ConvertTo-Json -Depth 6
  $r = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/chat" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
  $content = $r.message.content | ConvertFrom-Json
  if ($content.status -ne "PASS") { throw "Unexpected model response." }
  Write-Host "PASS: local VLM responded correctly."
} catch {
  Write-Error $_
  exit 1
}
