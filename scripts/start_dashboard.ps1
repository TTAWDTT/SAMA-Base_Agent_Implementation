$ErrorActionPreference = "Stop"

$root = Resolve-Path "$PSScriptRoot\\.."
Set-Location $root

python main.py --dashboard
