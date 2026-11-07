$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
& (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') tools/run_kadr.py
