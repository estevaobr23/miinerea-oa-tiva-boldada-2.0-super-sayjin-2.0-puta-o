$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONPATH = (Join-Path $PSScriptRoot "src")
& .\.venv\Scripts\python.exe -m uvicorn mineracao_info.server:app --host 127.0.0.1 --port 8791
