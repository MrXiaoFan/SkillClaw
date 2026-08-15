$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Missing virtualenv python: $python"
}

& $python -m skillclaw.cli dashboard serve `
  --host 127.0.0.1 `
  --port 3788 `
  --sharing-local-root "$repoRoot\skillspace\share" `
  --sharing-group-id default `
  --sharing-user-alias Fan `
  --evolve-server-url http://127.0.0.1:8787
