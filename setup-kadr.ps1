$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:UV_CACHE_DIR = Join-Path $PSScriptRoot '.cache\uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PSScriptRoot '.cache\python'
$env:PYTHONUTF8 = '1'
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.kadr.example' -Destination '.env' }
uv python install 3.10.9
if ($LASTEXITCODE -ne 0) { throw 'Python installation failed' }
uv sync --no-default-groups --group course
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& '.\.venv\Scripts\python.exe' tools/download_voice.py
if ($LASTEXITCODE -ne 0) { throw 'Voice download failed' }
Write-Output 'Add OPENAI_API_KEY to .env, then run .\run-kadr.ps1'
