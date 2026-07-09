param(
    [string]$HostName = "li@192.168.1.4",
    [string]$KeyPath = "$env:USERPROFILE\.ssh\skillclaw_vm",
    [string]$Session = "codex-live",
    [string]$Command = "",
    [string]$CommandFile = ""
)

$ErrorActionPreference = "Stop"

if ($CommandFile) {
    $CommandText = [System.IO.File]::ReadAllText((Resolve-Path $CommandFile), [System.Text.Encoding]::UTF8)
} elseif ($Command) {
    $CommandText = $Command
} else {
    $CommandText = [Console]::In.ReadToEnd()
}

if (-not $CommandText.Trim()) {
    throw "No command text provided. Use -Command, -CommandFile, or pipe text into this script."
}

$Payload = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($CommandText))
$RemoteScript = @"
set -e
tmp=`$(mktemp)
base64 -d > "`$tmp" <<'B64'
$Payload
B64
tmux load-buffer "`$tmp"
tmux paste-buffer -d -t '$Session':0.0
tmux send-keys -t '$Session':0.0 Enter
rm -f "`$tmp"
"@

$RemoteScript | ssh -i $KeyPath $HostName "bash -s"
