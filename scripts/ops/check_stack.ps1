$ErrorActionPreference = "Stop"

Write-Host "SkillClaw:"
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:30000/healthz | Select-Object -ExpandProperty Content

Write-Host ""
Write-Host "Evolve:"
Invoke-RestMethod http://127.0.0.1:8787/status | ConvertTo-Json -Depth 4

Write-Host ""
Write-Host "Dashboard:"
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:3788/).StatusCode
