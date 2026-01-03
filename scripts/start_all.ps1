$ErrorActionPreference = "Stop"

$root = Resolve-Path "$PSScriptRoot\\.."
$rootPath = $root.Path

Start-Process -FilePath "powershell" -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$rootPath'; python main.py --chat-ui"
)

Start-Process -FilePath "powershell" -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$rootPath'; python main.py --dashboard"
)
