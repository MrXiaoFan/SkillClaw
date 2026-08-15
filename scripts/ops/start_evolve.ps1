$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Missing virtualenv python: $python"
}

& $python -m evolve_server `
  --use-skillclaw-config `
  --engine workflow `
  --local-root .\skillspace\share `
  --group-id default `
  --port 8787 `
  --publish-mode validated `
  --feedback-bundle runtime\evolve\skill_feedback_bundle.json
